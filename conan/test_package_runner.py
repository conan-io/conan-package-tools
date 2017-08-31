import json
import os
import pipes
import platform
import tempfile
from collections import namedtuple

from conan import __version__ as package_tools_version
from conan.log import logger
from conans.model.profile import Profile
from conans.tools import vcvars_command
from conans.util.files import save, mkdir


class TestPackageRunner(object):
    def __init__(self, profile, username, channel, mingw_installer_reference=None, runner=None,
                 args=None, conan_pip_package=None):

        self._profile = profile
        self._mingw_installer_reference = mingw_installer_reference
        self._args = args
        self._username = username
        self._channel = channel
        self._conan_pip_package = conan_pip_package
        self._runner = runner or os.system
        self.runner = runner

    @property
    def settings(self):
        return self._profile.settings

    @property
    def options(self):
        return self._profile.options

    def run(self):
        pre_command = None
        compiler = self.settings.get("compiler", None)
        if compiler == "Visual Studio" and "compiler.version" in self.settings:
            compiler_set = namedtuple("compiler", "version")(self.settings["compiler.version"])
            mock_sets = namedtuple("mock_settings",
                                   "arch compiler get_safe")(self.settings["arch"], compiler_set,
                                                             lambda x: self.settings.get(x, None))
            pre_command = vcvars_command(mock_sets)

        self._run_test_package(pre_command=pre_command)

    def _run_test_package(self, pre_command=None):
        # Save the profile in a tmp file
        tmp = os.path.join(tempfile.mkdtemp(suffix='conan_package_tools_profiles'), "profile")
        abs_profile_path = os.path.abspath(tmp)
        profile_txt = self._profile.dumps()
        save(abs_profile_path, profile_txt)
        command = "conan create %s/%s --profile %s %s" % (self._username, self._channel,
                                                          abs_profile_path, self._args)
        if pre_command:
            command = '%s && %s' % (pre_command, command)

        logger.info("******** RUNNING BUILD ********** \n%s\n\n%s" % (command, profile_txt))
        retcode = self._runner(command)
        if retcode != 0:
            exit("Error while executing:\n\t %s" % command)


def autodetect_docker_image(profile):
    compiler_name = profile.settings.get("compiler", None)
    compiler_version = profile.settings.get("compiler.version", None)
    if compiler_name not in ["clang", "gcc"]:
        raise Exception("Docker image cannot be autodetected for the compiler %s" % compiler_name)

    return "lasote/conan%s%s" % (compiler_name, compiler_version.replace(".", ""))


class DockerTestPackageRunner(TestPackageRunner):
    def __init__(self, profile, username, channel, mingw_ref=None, runner=None,
                 args=None, conan_pip_package=None, docker_image=None):

        self.docker_image = docker_image or autodetect_docker_image(profile)

        super(DockerTestPackageRunner, self).__init__(profile, username, channel,
                                                      mingw_installer_reference=mingw_ref,
                                                      runner=runner, args=args,
                                                      conan_pip_package=conan_pip_package)

    def run(self, pull_image=True):

        if pull_image:
            self.pull_image()
            # Update the downloaded image
            command = "sudo docker run --name conan_runner %s /bin/sh -c " \
                      "\"sudo pip install conan_package_tools==%s " \
                      "--upgrade" % (self.docker_image, package_tools_version)
            if self._conan_pip_package:
                command += " && sudo pip install %s\"" % self._conan_pip_package
            else:
                command += " && sudo pip install conan --upgrade\""

            self._runner(command)
            # Save the image with the updated installed
            # packages and remove the intermediate container
            self._runner("sudo docker commit conan_runner %s" % self.docker_image)
            self._runner("sudo docker rm conan_runner")

        # Run the build
        serial = pipes.quote(self.serialize())
        env_vars = "-e CONAN_RUNNER_ENCODED=%s -e CONAN_USERNAME=%s " \
                   "-e CONAN_CHANNEL=%s" % (serial, self._username, self._channel)

        command = "sudo docker run --rm -v %s:/home/conan/project -v " \
                  "~/.conan/:/home/conan/.conan -it %s %s /bin/sh -c \"" \
                  "rm -f /home/conan/.conan/conan.conf && cd project && " \
                  "run_test_package_in_docker\"" % (os.getcwd(), env_vars, self.docker_image)
        ret = self._runner(command)
        if ret != 0:
            raise Exception("Error building: %s" % command)

    def pull_image(self):
        datadir = os.path.expanduser("~/.conan/data")
        if not os.path.exists(datadir):
            mkdir(datadir)
            if platform.system() != "Windows":
                self._runner("chmod -R 777 %s" % datadir)
        logger.info("Pulling docker image %s" % self.docker_image)
        self._runner("sudo docker pull %s" % self.docker_image)

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
        if hasattr(Profile, "loads"):
            profile = Profile.loads(the_json["profile"])
        else:
            # Fixme, make public in conan?
            from conans.client.profile_loader import _load_profile
            profile = _load_profile(the_json["profile"], None, None)[0]
        ret = TestPackageRunner(profile,
                                username=the_json["username"],
                                channel=the_json["channel"],
                                args=the_json["args"],
                                conan_pip_package=the_json["conan_pip_package"])
        return ret
