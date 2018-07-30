import os
import sys
from collections import namedtuple

from conans import tools

from cpt import __version__ as package_tools_version
from cpt.printer import Printer
from cpt.profiles import load_profile, patch_default_base_profile


class CreateRunner(object):

    def __init__(self, profile_abs_path, reference, conan_api, uploader, args=None,
                 exclude_vcvars_precommand=False, build_policy=None, runner=None,
                 abs_folder=None, printer=None, upload=False, upload_retry=None, test_folder=None):

        self.printer = printer or Printer()
        self._abs_folder = abs_folder or os.getcwd()
        self._uploader = uploader
        self._upload = upload
        self._conan_api = conan_api
        self._profile_abs_path = profile_abs_path
        self._reference = reference
        self._args = args
        self._exclude_vcvars_precommand = exclude_vcvars_precommand
        self._build_policy = build_policy
        self._runner = PrintRunner(runner or os.system, self.printer)
        self._uploader.remote_manager.add_remotes_to_conan()
        self._test_folder = test_folder

        patch_default_base_profile(conan_api, profile_abs_path)
        self._profile = load_profile(profile_abs_path, self._conan_api._client_cache)

    @property
    def settings(self):
        return self._profile.settings

    def run(self):
        context = tools.no_op()
        compiler = self.settings.get("compiler", None)
        if not self._exclude_vcvars_precommand:
            if compiler == "Visual Studio" and "compiler.version" in self.settings:
                compiler_set = namedtuple("compiler", "version")(self.settings["compiler.version"])
                mock_sets = namedtuple("mock_settings",
                                       "arch compiler get_safe")(self.settings["arch"], compiler_set,
                                                                 lambda x: self.settings.get(x, None))
                context = tools.vcvars(mock_sets)
        with context:
            self.printer.print_rule()
            self.printer.print_profile(tools.load(self._profile_abs_path))

            with self.printer.foldable_output("conan_create"):
                name, version, user, channel = self._reference
                # print_dict
                # TODO: Get uploaded packages with Conan 1.3 from the ret json

                # FIXME: chdir Can be removed in 1.3, fixed issue about api changing curdir
                with tools.chdir(self._abs_folder):
                    if self._build_policy:
                        self._build_policy = [self._build_policy]
                    # https://github.com/conan-io/conan-package-tools/issues/184
                    with tools.environment_append({"_CONAN_CREATE_COMMAND_": "1"}):
                        params = {"name": name, "version": version, "user": user,
                                  "channel": channel, "build_modes": self._build_policy,
                                  "profile_name": self._profile_abs_path}
                        self.printer.print_message("Calling 'conan create'")
                        self.printer.print_dict(params)

                        self._conan_api.create(".", name=name, version=version,
                                               user=user, channel=channel,
                                               build_modes=self._build_policy,
                                               profile_name=self._profile_abs_path,
                                               test_folder=self._test_folder)

                self._uploader.upload_packages(self._reference, self._upload)


class DockerCreateRunner(object):
    def __init__(self, profile_text, base_profile_text, base_profile_name, reference,
                 args=None, conan_pip_package=None, docker_image=None, sudo_docker_command=None,
                 sudo_pip_command=True,
                 docker_image_skip_update=False, build_policy=None,
                 docker_image_skip_pull=False,
                 always_update_conan_in_docker=False,
                 upload=False, upload_retry=None,
                 runner=None,
                 docker_shell="", docker_conan_home="",
                 docker_platform_param="", lcow_user_workaround="",
                 test_folder=None):

        self.printer = Printer()
        self._args = args
        self._upload = upload
        self._upload_retry = upload_retry
        self._reference = reference
        self._conan_pip_package = conan_pip_package
        self._build_policy = build_policy
        self._docker_image = docker_image
        self._always_update_conan_in_docker = always_update_conan_in_docker
        self._docker_image_skip_update = docker_image_skip_update
        self._docker_image_skip_pull = docker_image_skip_pull
        self._sudo_docker_command = sudo_docker_command or ""
        self._sudo_pip_command = sudo_pip_command
        self._profile_text = profile_text
        self._base_profile_text = base_profile_text
        self._base_profile_name = base_profile_name
        self._docker_shell = docker_shell
        self._docker_conan_home = docker_conan_home
        self._docker_platform_param = docker_platform_param
        self._lcow_user_workaround = lcow_user_workaround
        self._runner = PrintRunner(runner, self.printer)
        self._test_folder = test_folder

    def _pip_update_conan_command(self):
        commands = []
        # Hack for testing when retrieving cpt from artifactory repo
        if "conan-package-tools" not in self._conan_pip_package:
            commands.append("%s pip install conan_package_tools==%s "
                            "--upgrade --no-cache" % (self._sudo_pip_command,
                                                      package_tools_version))

        if self._conan_pip_package:
            commands.append("%s pip install %s --no-cache" % (self._sudo_pip_command,
                                                              self._conan_pip_package))
        else:
            commands.append("%s pip install conan --upgrade --no-cache" % self._sudo_pip_command)

        command = " && ".join(commands)
        return command

    def run(self, pull_image=True, docker_entry_script=None):
        envs = self.get_env_vars()
        env_vars_text = " ".join(['-e %s="%s"' % (key, value)
                                 for key, value in envs.items() if value])

        # Run the build
        if pull_image:
            if not self._docker_image_skip_pull:
                self.pull_image()
            if not self._docker_image_skip_update and not self._always_update_conan_in_docker:
                # Update the downloaded image
                with self.printer.foldable_output("update conan"):
                    try:
                        command = '%s docker run %s --name conan_runner ' \
                                  ' %s %s "%s"' % (self._sudo_docker_command,
                                                   env_vars_text,
                                                   self._docker_image,
                                                   self._docker_shell,
                                                   self._pip_update_conan_command())

                        ret = self._runner(command)
                        if ret != 0:
                            raise Exception("Error updating the image: %s" % command)
                        # Save the image with the updated installed
                        # packages and remove the intermediate container
                        command = "%s docker commit conan_runner %s" % (self._sudo_docker_command,
                                                                        self._docker_image)
                        ret = self._runner(command)
                        if ret != 0:
                            raise Exception("Error commiting the image: %s" % command)
                    finally:
                        command = "%s docker rm conan_runner" % self._sudo_docker_command
                        ret = self._runner(command)
                        if ret != 0:
                            raise Exception("Error removing the temp container: %s" % command)

        if self._always_update_conan_in_docker:
            update_command = self._pip_update_conan_command() + " && "
        else:
            update_command = ""
        command = ('%s docker run --rm -v %s:%s/project %s %s %s %s '
                   '"%s cd project && '
                   '%s run_create_in_docker "' % (self._sudo_docker_command,
                                                  os.getcwd(),
                                                  self._docker_conan_home,
                                                  env_vars_text,
                                                  self._docker_platform_param,
                                                  self._docker_image,
                                                  self._docker_shell,
                                                  self._lcow_user_workaround,
                                                  update_command))

        # Push entry command before to build
        if docker_entry_script:
            command = command.replace("run_create_in_docker",
                                      "%s && run_create_in_docker" % docker_entry_script)

        self.printer.print_in_docker(self._docker_image)
        ret = self._runner(command)
        if ret != 0:
            raise Exception("Error building: %s" % command)
        self.printer.print_message("Exiting docker...")

    def pull_image(self):
        with self.printer.foldable_output("docker pull"):
            ret = self._runner("%s docker pull %s" % (self._sudo_docker_command, self._docker_image))
            if ret != 0:
                raise Exception("Error pulling the image: %s" % self._docker_image)

    def get_env_vars(self):
        ret = {key: value for key, value in os.environ.items() if key.startswith("CONAN_") and
               key != "CONAN_USER_HOME"}
        ret["CPT_ARGS"] = escape_env(self._args)
        ret["CONAN_REFERENCE"] = self._reference

        ret["CPT_PROFILE"] = escape_env(self._profile_text)
        ret["CPT_BASE_PROFILE"] = escape_env(self._base_profile_text)
        ret["CPT_BASE_PROFILE_NAME"] = escape_env(self._base_profile_name)

        ret["CONAN_USERNAME"] = escape_env(self._reference.user)
        ret["CONAN_TEMP_TEST_FOLDER"] = "1"  # test package folder to a temp one
        ret["CPT_UPLOAD_ENABLED"] = self._upload
        ret["CPT_UPLOAD_RETRY"] = self._upload_retry
        ret["CPT_BUILD_POLICY"] = escape_env(self._build_policy)
        ret["CPT_TEST_FOLDER"] = escape_env(self._test_folder)

        ret.update({key: value for key, value in os.environ.items() if key.startswith("PIP_")})

        return ret


def unscape_env(text):
    if not text:
        return text
    return text.replace("@@", "\n").replace('||', '"')


def escape_env(text):
    if not text:
        return text
    return text.replace("\n", "@@").replace('"', '||')


class PrintRunner(object):

    def __init__(self, runner, printer):
        self.runner = runner
        self.printer = printer

    def __call__(self, command):
        self.printer.print_command(command)
        sys.stderr.flush()
        sys.stdout.flush()
        return self.runner(command)
