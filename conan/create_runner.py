import json
import os
import pipes
import platform
import tempfile
from collections import namedtuple

import shutil

from conan import __version__ as package_tools_version
from conan.log import logger
from conan.printer import print_message, print_profile, print_rule, foldable_output, print_command
from conan.tools import get_bool_from_env
from conans.client.conan_api import Conan
from conans.client.profile_loader import _load_profile
from conans.model.version import Version
from conans.tools import vcvars_command
from conans.util.files import save, mkdir
from conans import __version__ as client_version


class TestPackageRunner(object):
    def __init__(self, profile_text, username, channel, reference,
                 mingw_installer_reference=None, runner=None,
                 args=None, conan_pip_package=None,
                 exclude_vcvars_precommand=False,
                 conan_vars=None, build_policy=None):

        self._conan_vars = conan_vars or {}
        self._profile_text = profile_text
        self._mingw_installer_reference = mingw_installer_reference
        self._args = args
        self._args += " --build=%s" % build_policy if build_policy else ""
        self._username = username
        self._channel = channel
        self._reference = reference
        self._conan_pip_package = conan_pip_package
        self._runner = runner or os.system
        self.runner = self._runner
        self.conan_api, self.client_cache, self.user_io = Conan.factory()
        self.conan_home = os.path.realpath(self.client_cache.conan_folder)
        self.data_home = os.path.realpath(self.client_cache.store)
        self._exclude_vcvars_precommand = exclude_vcvars_precommand

        if "default" in self._profile_text:  # User didn't specified a custom profile
            default_profile_name = os.path.basename(self.client_cache.default_profile_path)
            if not os.path.exists(self.client_cache.default_profile_path):
                self.conan_api.create_profile(default_profile_name, detect=True)

            if default_profile_name != "default":  # User have a different default profile name
                # https://github.com/conan-io/conan-package-tools/issues/121
                self._profile_text = self._profile_text.replace("include(default)",
                                                                "include(%s)" % default_profile_name)

        # Save the profile in a tmp file
        tmp = os.path.join(tempfile.mkdtemp(suffix='conan_package_tools_profiles'), "profile")
        self.abs_profile_path = os.path.abspath(tmp)
        save(self.abs_profile_path, self._profile_text)

        self.profile, _ = _load_profile(self._profile_text, os.path.dirname(self.abs_profile_path),
                                        self.client_cache.profiles_path)

    @property
    def settings(self):
        return self.profile.settings

    @property
    def options(self):
        return self.profile.options

    def run(self):
        pre_command = None
        compiler = self.settings.get("compiler", None)
        if not self._exclude_vcvars_precommand:
            if compiler == "Visual Studio" and "compiler.version" in self.settings:
                compiler_set = namedtuple("compiler", "version")(self.settings["compiler.version"])
                mock_sets = namedtuple("mock_settings",
                                       "arch compiler get_safe")(self.settings["arch"], compiler_set,
                                                                 lambda x: self.settings.get(x, None))
                pre_command = vcvars_command(mock_sets)

        self._run_create(pre_command=pre_command)

    def _run_create(self, pre_command=None):

        if Version(client_version) < Version("0.99"):  # Introduced in 1.0.0-beta.1
            path = ""
        else:
            path = "."

        ref = self._reference if self._reference else "%s/%s" % (self._username, self._channel)
        command = "conan create %s %s --profile %s %s" % (path, str(ref), self.abs_profile_path,
                                                          self._args)

        if pre_command:
            command = '%s && %s' % (pre_command, command)

        print_command(command)
        print_rule()
        print_profile(self._profile_text)

        with foldable_output("conan_create"):
            retcode = self._runner(command)
            if retcode != 0:
                exit("Error while executing:\n\t %s" % command)


def autodetect_docker_base_image(profile):
    compiler_name = profile.settings.get("compiler", None)
    compiler_version = profile.settings.get("compiler.version", None)
    if compiler_name not in ["clang", "gcc"]:
        raise Exception("Docker image cannot be autodetected for the compiler %s" % compiler_name)

    if compiler_name == "gcc" and Version(compiler_version) > Version("5"):
        compiler_version = Version(compiler_version).major(fill=False)

    return "lasote/conan%s%s" % (compiler_name, compiler_version.replace(".", ""))


class DockerTestPackageRunner(TestPackageRunner):
    def __init__(self, profile_text, username, channel, reference, mingw_ref=None, runner=None,
                 args=None, conan_pip_package=None, docker_image=None,
                 docker_image_skip_update=False, docker_arch_suffix=None, build_policy=None):

        super(DockerTestPackageRunner, self).__init__(profile_text, username, channel, reference,
                                                      mingw_installer_reference=mingw_ref,
                                                      runner=runner, args=args,
                                                      conan_pip_package=conan_pip_package,
                                                      build_policy=build_policy)

        self.docker_image = docker_image or autodetect_docker_base_image(self.profile)
        if docker_arch_suffix and "-" not in self.docker_image:
            self.docker_image += "-%s" % docker_arch_suffix

        self.docker_image_skip_update = docker_image_skip_update
        self.sudo_command = ""
        if "CONAN_DOCKER_USE_SUDO" in os.environ:
            if get_bool_from_env("CONAN_DOCKER_USE_SUDO"):
                self.sudo_command = "sudo"
        elif platform.system() == "Linux":
            self.sudo_command = "sudo"

        # Below is all supporting Docker on Windows
        # wcow : windows container on windows
        # lcow : linux container on windows
        conan_conf = ".conan/conan.conf"
        conan_profile = ".conan/profiles/default"
        self.docker_shell = ""
        # The sudo parameter for the command within the container
        self.docker_sudo_command = ""
        if self.is_wcow():
            self.docker_conan_home = "C:\\Users\\ContainerAdministrator"
            conf_win = conan_conf.replace("/", "\\")
            profile_win = conan_profile.replace("/", "\\")
            conf = "%s\\%s" % (self.docker_conan_home, conf_win)
            profile = "%s\\%s" % (self.docker_conan_home, profile_win)
            self.delete_conf_cmd = "IF EXIST {0} del /f {0}".format(conf)
            self.delete_profile_cmd = "IF EXIST {0} del /f {0}".format(profile)
            self.docker_shell = "cmd /C"
        else:  # For both docker on Linux and Linux containers on Windows
            if self.is_lcow():
                self.docker_conan_home = "/root"
            else:
                self.docker_conan_home = "/home/conan"
            conf = "%s/%s" % (self.docker_conan_home, conan_conf)
            profile = "%s/%s" % (self.docker_conan_home, conan_profile)
            self.delete_conf_cmd = "rm -f %s" % conf
            self.delete_profile_cmd = "rm -f %s" % profile
            self.docker_shell = "/bin/sh -c"
            self.docker_sudo_command = "sudo"

        if self.is_lcow():
            self.docker_platform = "--platform=linux"
        else:
            self.docker_platform = ""

    # For Docker on Windows, including Linux containers on Windows
    def is_lcow(self):
        return self.get_container_os() == "linux"

    def is_wcow(self):
        return self.get_container_os() == "windows"

    def get_container_os(self):
        # CONAN_DOCKER_PLATFORM=linux must be specified for LCOW
        if "CONAN_DOCKER_PLATFORM" in os.environ:
            return os.getenv("CONAN_DOCKER_PLATFORM", "windows").lower()
        else:
            return "windows"

    def clear_system_requirements(self):
        if self._reference:
            the_path = self.client_cache.system_reqs(self._reference)
            if os.path.exists(the_path):
                logger.info("Removing system_requirements: %s" % the_path)
                shutil.rmtree(os.path.dirname(the_path), ignore_errors=True)

    def run(self, pull_image=True, docker_entry_script=None):
        if pull_image:
            self.pull_image()
            if not self.docker_image_skip_update:
                # Update the downloaded image
                command = "{sudo} docker run --user conan {platform} --name conan_runner " \
                          "{docker_image} {shell} \"" \
                          "{docker_sudo} pip install conan_package_tools=={version} " \
                          "--upgrade".format(
                                        sudo=self.sudo_command,
                                        platform=self.docker_platform,
                                        docker_image=self.docker_image,
                                        shell=self.docker_shell,
                                        docker_sudo=self.docker_sudo_command,
                                        version=package_tools_version)

                with foldable_output("update conan"):
                    if self._conan_pip_package:
                        command += " && %s pip install %s\"" % \
                                   (self.docker_sudo_command, self._conan_pip_package)
                    else:
                        command += " && %s pip install conan --upgrade\"" % \
                                   self.docker_sudo_command
                    print_command(command)
                    self._runner(command)
                    # Save the image with the updated installed
                    # packages and remove the intermediate container
                    command = "%s docker commit conan_runner %s" % (self.sudo_command, self.docker_image)
                    print_message(command)
                    self._runner(command)

                    command = "%s docker rm conan_runner" % self.sudo_command
                    print_command(command)
                    self._runner(command)

        # Run the build
        serial = pipes.quote(self.serialize())
        if platform.system() == "Windows":
            serial = serial.replace('"', '\\"').replace("'", '"')

        env_vars = "-e CONAN_RUNNER_ENCODED=%s -e CONAN_USERNAME=%s " \
                   "-e CONAN_CHANNEL=%s" % (serial, self._username, self._channel)

        conan_env_vars = {key: value for key, value in os.environ.items()
                          if key.startswith("CONAN_") and key not in
                          ["CONAN_CHANNEL", "CONAN_USERNAME", "CONAN_USER_HOME"]}
        env_vars += " " + " ".join(['-e %s="%s"' % (key, value) for key, value in conan_env_vars.items()])

        command = "{sudo} docker run {platform} --rm " \
            "-v {cwd}:{docker_conan_home}/project " \
            "-v {conan_home}:{docker_conan_home}/.conan " \
            "{env_vars} {docker_image} {shell} " \
            "\"cd {docker_conan_home}/project && " \
            "{delete_profile} && " \
            "(conan profile new default --detect || true) && " \
            "run_create_in_docker\"".format(
                            sudo=self.sudo_command,
                            platform=self.docker_platform,
                            cwd=os.getcwd(),
                            docker_conan_home=self.docker_conan_home,
                            conan_home=self.conan_home,
                            env_vars=env_vars,
                            docker_image=self.docker_image,
                            shell=self.docker_shell,
                            delete_conf=self.delete_conf_cmd,
                            delete_profile=self.delete_profile_cmd)

        # Push entry command before to build
        if docker_entry_script:
            command = command.replace("run_create_in_docker", "%s && run_create_in_docker" % docker_entry_script)

        self.clear_system_requirements()
        ret = self._runner(command)
        if ret != 0:
            raise Exception("Error building: %s" % command)

    def pull_image(self):
        datadir = os.path.expanduser(self.data_home)
        if not os.path.exists(datadir):
            mkdir(datadir)
            if platform.system() != "Windows":
                self._runner("chmod -R 777 %s" % datadir)
        with foldable_output("docker pull"):
            print_message("Pulling docker image %s" % self.docker_image)
            self._runner("%s docker pull %s" % (self.sudo_command, self.docker_image))

    def serialize(self):
        doc = {"args": self._args,
               "username": self._username,
               "channel": self._channel,
               "profile": self._profile_text,
               "conan_pip_package": self._conan_pip_package,
               "reference": str(self._reference)}
        return json.dumps(doc)

    @staticmethod
    def deserialize(data):
        the_json = json.loads(data)
        ret = TestPackageRunner(the_json["profile"],
                                username=the_json["username"],
                                channel=the_json["channel"],
                                reference=the_json["reference"],
                                args=the_json["args"],
                                conan_pip_package=the_json["conan_pip_package"])
        return ret
