import os
import platform
import tempfile
from collections import namedtuple

import shutil

from cpt import __version__ as package_tools_version
from cpt.log import logger
from cpt.printer import print_message, print_profile, print_rule, foldable_output, print_command
from cpt.tools import get_bool_from_env
from conans.client.conan_api import Conan
from conans.client.profile_loader import _load_profile
from conans.model.version import Version
from conans.tools import vcvars_command
from conans.util.files import save, mkdir
from conans import __version__ as client_version


class TestPackageRunner(object):
    def __init__(self, profile_text=None, username=None, channel=None, reference=None, runner=None,
                 args=None, conan_pip_package=None, exclude_vcvars_precommand=False,
                 build_policy=None):

        self._profile_text = profile_text or os.getenv("CPT_PROFILE")
        self._args = args or os.getenv("CPT_ARGS", "")
        self._build_policy = build_policy or os.getenv("CPT_BUILD_POLICY")

        self._username = username or os.getenv("CONAN_USERNAME")
        self._channel = channel or os.getenv("CONAN_CHANNEL")
        self._reference = reference or os.getenv("CONAN_REFERENCE")
        self._conan_pip_package = conan_pip_package or os.getenv("CPT_PIP_PACKAGE")
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
        bp_command = " --build=%s" % self._build_policy if self._build_policy else ""
        command = "conan create %s %s --profile %s %s %s" % (path, str(ref), self.abs_profile_path,
                                                             self._args, bp_command)

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
    def __init__(self, profile_text, username=None, channel=None, reference=None, runner=None,
                 args=None, conan_pip_package=None, docker_image=None,
                 docker_image_skip_update=False, docker_arch_suffix=None, build_policy=None):

        super(DockerTestPackageRunner, self).__init__(profile_text, username, channel, reference,
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
                with foldable_output("update conan"):
                    command = "%s docker run --name conan_runner %s /bin/sh -c " \
                            "\"sudo pip install conan_package_tools==%s " \
                            "--upgrade" % (self.sudo_command, self.docker_image, package_tools_version)
                    if self._conan_pip_package:
                        command += " && sudo pip install %s\"" % self._conan_pip_package
                    else:
                        command += " && sudo pip install conan --upgrade\""

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
        envs = self.get_env_vars()
        env_vars_text = " " + " ".join(['-e %s="%s"' % (key, value) for key, value in envs.items()])

        command = "%s docker run --rm -v %s:/home/conan/project %s %s /bin/sh -c \"" \
                  "cd project && " \
                  "run_create_in_docker\"" % (self.sudo_command, os.getcwd(),
                                              env_vars_text, self.docker_image)

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

    def get_env_vars(self):
        ret = {key: value for key, value in os.environ.items() if key.startswith("CONAN_")}
        ret["CPT_ARGS"] = self._args
        ret["CONAN_USERNAME"] = self._username
        ret["CONAN_CHANNEL"] = self._channel
        ret["CONAN_REFERENCE"] = self._reference
        ret["CPT_PROFILE"] = self._profile_text
        ret["CPT_PIP_PACKAGE"] = self._conan_pip_package
        ret["CPT_BUILD_POLICY"] = self._build_policy

        return ret

