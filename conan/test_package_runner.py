import collections
import json
import os
import pipes
import platform
import tempfile

from conan.log import logger
from conans.model.profile import Profile
from conans.tools import vcvars_command
from conans.util.files import save, load


class TestPackageRunner(object):

    def __init__(self, profile, username, channel, mingw_installer_reference=None, runner=None, args=None,
                 conan_pip_package=None):

        self._profile = profile
        self._mingw_installer_reference = mingw_installer_reference
        self._args = args
        self._username = username
        self._channel = channel
        self._conan_pip_package = conan_pip_package

        self._runner = runner or os.system


    @property
    def settings(self):
        return self._profile.settings

    @property
    def options(self):
        return self._profile.options

    def run(self):
        pre_command = None
        if self.settings.get("compiler", None) == "Visual Studio" and "compiler.version" in self.settings:
            pre_command = vcvars_command(self.settings)
        elif self.settings.get("compiler", None) == "gcc" and platform.system() == "Windows":
            if self._mingw_installer_reference:
                self._add_mingw_build_require()

        self._run_test_package(pre_command=pre_command)

    def _run_test_package(self, pre_command=None):
        settings = collections.OrderedDict(sorted(self.settings.items()))
        if platform.system() != "Windows":
            if settings.get("compiler", None) and settings.get("compiler.version", None):
                conan_compiler, conan_compiler_version = self.conan_compiler_info()
                if conan_compiler != settings.get("compiler", None) or \
                   conan_compiler_version != settings.get("compiler.version", None):
                    logger.debug("- Skipped build, compiler mismatch: %s" % str(dict(settings)))
                    return  # Skip this build, it's not for this machine

        # Save the profile in a tmp file
        abs_profile_path = os.path.abspath(os.path.join(tempfile.mkdtemp(suffix='conan_package_tools_profiles'),
                                                        "profile"))
        save(abs_profile_path, self._profile.dumps())
        command = "conan test_package . --profile %s %s" % (abs_profile_path, self._args)
        if pre_command:
            command = '%s && %s' % (pre_command, command)

        logger.info("******** RUNNING BUILD ********** \n%s" % command)
        retcode = self._runner(command)
        if retcode != 0:
            exit("Error while executing:\n\t %s" % command)

    def _add_mingw_build_require(self):
        """"FIXME REPLACE WITH A BUILD REQUIRE WITH OPTIONS"""
        installer_options = []
        for setting in ("compiler.threads", "compiler.exception", "compiler.version", "arch"):
            setting_value = self.settings.get(setting, None)
            if setting_value:
                short_name = setting.split(".", 1)[-1]
                installer_options.append((short_name, setting_value))

        self._profile.options.loads("\n".join(["%s=%s" % (v[0], v[1]) for v in installer_options]))
        self._profile.build_requires["*"] = [self._mingw_installer_reference]

    def conan_compiler_info(self):
        """return the compiler and its version readed in conan.conf"""
        from six.moves import configparser
        parser = configparser.ConfigParser()
        home = os.environ.get("CONAN_USER_HOME", "~/")
        conf_path = os.path.expanduser("%s/.conan/conan.conf" % home)
        if "compiler.version" not in load(conf_path):
            self._runner("conan user")  # Force default settings autodetection
        parser.read(conf_path)
        items = dict(parser.items("settings_defaults"))
        return items["compiler"], items["compiler.version"]


class DockerTestPackageRunner(TestPackageRunner):

    def __init__(self, profile, username, channel, mingw_installer_reference=None, runner=None, args=None,
                 conan_pip_package=None, docker_image=None):

        gcc_version = profile.settings.get("compiler.version").replace(".", "")
        self._docker_image = docker_image or "lasote/conangcc%s" % gcc_version
        super(DockerTestPackageRunner, self).__init__(profile, username, channel,
                                                      mingw_installer_reference=mingw_installer_reference,
                                                      runner=runner, args=args, conan_pip_package=conan_pip_package)

    def run(self):
        self.pull_image()
        serial = pipes.quote(self.serialize())
        env_vars = "-e CONAN_RUNNER_ENCODED=%s -e CONAN_USERNAME=%s " \
                   "-e CONAN_CHANNEL=%s" % (serial, self._username, self._channel)

        if self._conan_pip_package:
            specific_conan_package = "&& sudo pip install %s" % self._conan_pip_package
        else:
            specific_conan_package = "&& sudo pip install conan --upgrade"

        command = "sudo docker run --rm -v %s:/home/conan/project -v " \
                  "~/.conan/data:/home/conan/.conan/data -it %s %s /bin/sh -c \"" \
                  "cd project && sudo pip install conan_package_tools --upgrade %s && " \
                  "run_test_package_in_docker\"" % (os.getcwd(), env_vars, self._docker_image, specific_conan_package)
        ret = self._runner(command)
        if ret != 0:
            raise Exception("Error building: %s" % command)

    def pull_image(self):
        if not os.path.exists(os.path.expanduser("~/.conan/data")):
            self._runner("mkdir ~/.conan/data && chmod -R 777 ~/.conan/data")
        logger.info("Pulling docker image %s" % self._docker_image)
        self._runner("sudo docker pull %s" % self._docker_image)

    def serialize(self):
        doc = {"args": self._args,
               "username": self._username,
               "channel": self._channel,
               "profile": self._profile.dumps(),
               "conan_pip_package": self._conan_pip_package}
        return json.dumps(doc)

    @staticmethod
    def deserialize(data):
        the_json = json.loads(data)
        profile = Profile.loads(the_json["profile"])
        ret = TestPackageRunner(profile,
                                username=the_json["username"],
                                channel=the_json["channel"],
                                args=the_json["args"],
                                conan_pip_package=the_json["conan_pip_package"])
        return ret
