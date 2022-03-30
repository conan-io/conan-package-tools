import os
import sys
import subprocess
import re
import time
from collections import namedtuple

from conans import tools
from conans.model.version import Version
from conans.model.ref import ConanFileReference

from cpt import __version__ as package_tools_version, get_client_version
from cpt.config import ConfigManager
from cpt.printer import Printer
from cpt.profiles import load_profile, patch_default_base_profile
from conans.client.conan_api import ProfileData


class CreateRunner(object):

    def __init__(self, profile_abs_path, reference, conan_api, uploader,
                 exclude_vcvars_precommand=False, build_policy=None, require_overrides=None, runner=None,
                 cwd=None, printer=None, upload=False, upload_only_recipe=None,
                 test_folder=None, config_url=None, config_args=None,
                 upload_dependencies=None, conanfile=None, skip_recipe_export=False,
                 update_dependencies=False, lockfile=None, profile_build_abs_path=None):

        self.printer = printer or Printer()
        self._cwd = cwd or os.getcwd()
        self._uploader = uploader
        self._upload = upload
        self._conan_api = conan_api
        self._profile_abs_path = profile_abs_path
        self._reference = reference
        self._exclude_vcvars_precommand = exclude_vcvars_precommand
        self._build_policy = build_policy.split(",") if \
                             isinstance(build_policy, str) else \
                             build_policy
        self._require_overrides = require_overrides.split(",") if \
                             isinstance(require_overrides, str) else \
                             require_overrides
        self._runner = PrintRunner(runner or os.system, self.printer)
        self._test_folder = test_folder
        self._config_url = config_url
        self._config_args = config_args
        self._upload_only_recipe = upload_only_recipe
        self._conanfile = conanfile
        self._lockfile = lockfile
        self._upload_dependencies = upload_dependencies.split(",") if \
                                    isinstance(upload_dependencies, str) else \
                                    upload_dependencies
        self._upload_dependencies = self._upload_dependencies or []
        self.skip_recipe_export = skip_recipe_export
        self._update_dependencies = update_dependencies
        self._results = None
        self._profile_build_abs_path = profile_build_abs_path

        patch_default_base_profile(conan_api, profile_abs_path)
        client_version = get_client_version()

        if client_version < Version("1.12.0"):
            cache = self._conan_api._client_cache
        elif client_version < Version("1.18.0"):
            cache = self._conan_api._cache
        else:
            if not conan_api.app:
                conan_api.create_app()
            cache = conan_api.app.cache

        self._profile = load_profile(profile_abs_path, cache)

        if isinstance(self._test_folder, str) and self._test_folder.lower() == "false":
            self._test_folder = False

    @property
    def settings(self):
        return self._profile.settings

    @property
    def results(self):
        return self._results

    def run(self):
        client_version = get_client_version()

        if self._config_url:
            ConfigManager(self._conan_api, self.printer).install(url=self._config_url, args=self._config_args)

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

            if self._profile_build_abs_path is not None:
                self.printer.print_profile(tools.load(self._profile_build_abs_path))

            with self.printer.foldable_output("conan_create"):
                if client_version < Version("1.10.0"):
                    name, version, user, channel = self._reference
                else:
                    name, version, user, channel, _ = self._reference

                if self._build_policy:
                    self._build_policy = [] if self._build_policy == ["all"] else self._build_policy
                # https://github.com/conan-io/conan-package-tools/issues/184
                with tools.environment_append({"_CONAN_CREATE_COMMAND_": "1"}):
                    params = {"name": name, "version": version, "user": user,
                              "channel": channel, "build_modes": self._build_policy,
                              "require_overrides": self._require_overrides,
                              "profile_name": self._profile_abs_path,
                              "profile_build_name": self._profile_build_abs_path}
                    self.printer.print_message("Calling 'conan create'")
                    self.printer.print_dict(params)
                    with tools.chdir(self._cwd):
                        if Version(client_version) >= "1.8.0":
                            from conans.errors import ConanInvalidConfiguration
                            exc_class = ConanInvalidConfiguration
                        else:
                            exc_class = None

                        try:
                            if client_version < Version("1.12.0"):
                                self._results = self._conan_api.create(self._conanfile, name=name, version=version,
                                                        user=user, channel=channel,
                                                        build_modes=self._build_policy,
                                                        require_overrides=self._require_overrides,
                                                        profile_name=self._profile_abs_path,
                                                        test_folder=self._test_folder,
                                                        not_export=self.skip_recipe_export,
                                                        update=self._update_dependencies)
                            else:
                                if self._profile_build_abs_path is not None:
                                    if client_version < Version("1.38.0"):
                                        profile_build = ProfileData(profiles=[self._profile_build_abs_path], settings=None,
                                                                    options=None, env=None)
                                    else:
                                        profile_build = ProfileData(profiles=[self._profile_build_abs_path], settings=None,
                                                                    options=None, env=None, conf=None)
                                else:
                                    profile_build = None

                                self._results = self._conan_api.create(self._conanfile, name=name, version=version,
                                                        user=user, channel=channel,
                                                        build_modes=self._build_policy,
                                                        require_overrides=self._require_overrides,
                                                        profile_names=[self._profile_abs_path],
                                                        test_folder=self._test_folder,
                                                        not_export=self.skip_recipe_export,
                                                        update=self._update_dependencies,
                                                        lockfile=self._lockfile,
                                                        profile_build=profile_build)
                        except exc_class as e:
                            self.printer.print_rule()
                            self.printer.print_message("Skipped configuration by the recipe: "
                                                       "%s" % str(e))
                            self.printer.print_rule()
                            return
                        for installed in self._results['installed']:
                            reference = installed["recipe"]["id"]
                            if client_version >= Version("1.10.0"):
                                reference = ConanFileReference.loads(reference)
                                reference = str(reference.copy_clear_rev())
                            if ((reference == str(self._reference)) or
                               (reference in self._upload_dependencies) or
                               ("all" in self._upload_dependencies)) and \
                               installed['packages']:
                                package_id = installed['packages'][0]['id']
                                if installed['packages'][0]["built"]:
                                    if "@" not in reference:
                                        reference += "@"
                                    if self._upload_only_recipe:
                                        self._uploader.upload_recipe(reference, self._upload)
                                    else:
                                        self._uploader.upload_packages(reference,
                                                                    self._upload, package_id)
                                else:
                                    self.printer.print_message("Skipping upload for %s, "
                                                               "it hasn't been built" % package_id)


class DockerCreateRunner(object):
    def __init__(self, profile_text, base_profile_text, base_profile_name, reference,
                 conan_pip_package=None, docker_image=None, sudo_docker_command=None,
                 sudo_pip_command=False,
                 docker_image_skip_update=False, build_policy=None, require_overrides=None,
                 docker_image_skip_pull=False,
                 always_update_conan_in_docker=False,
                 upload=False, upload_retry=None, upload_only_recipe=None,
                 upload_force=None,
                 runner=None,
                 docker_shell="", docker_conan_home="",
                 docker_platform_param="", docker_run_options="",
                 lcow_user_workaround="",
                 test_folder=None,
                 pip_install=None,
                 docker_pip_command=None,
                 config_url=None,
                 config_args=None,
                 printer=None,
                 upload_dependencies=None,
                 conanfile=None,
                 force_selinux=None,
                 skip_recipe_export=False,
                 update_dependencies=False,
                 lockfile=None,
                 profile_build_text=None,
                 base_profile_build_text=None,
                 cwd=None):

        self.printer = printer or Printer()
        self._upload = upload
        self._upload_retry = upload_retry
        self._upload_only_recipe = upload_only_recipe
        self._upload_force = upload_force
        self._reference = reference
        self._conan_pip_package = conan_pip_package
        self._build_policy = build_policy
        self._require_overrides = require_overrides
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
        self._docker_run_options = docker_run_options or ""
        self._lcow_user_workaround = lcow_user_workaround
        self._runner = PrintRunner(runner, self.printer)
        self._test_folder = test_folder
        self._pip_install = pip_install
        self._docker_pip_command = docker_pip_command
        self._config_url = config_url
        self._config_args = config_args
        self._upload_dependencies = upload_dependencies or []
        self._conanfile = conanfile
        self._lockfile = lockfile
        self._force_selinux = force_selinux
        self._skip_recipe_export = skip_recipe_export
        self._update_dependencies = update_dependencies
        self._profile_build_text = profile_build_text
        self._base_profile_build_text = base_profile_build_text
        self._cwd = cwd or os.getcwd()

    def _pip_update_conan_command(self):
        commands = []
        # Hack for testing when retrieving cpt from artifactory repo
        if "conan-package-tools" not in self._conan_pip_package:
            commands.append("%s %s install conan_package_tools==%s "
                            "--upgrade --no-cache" % (self._sudo_pip_command,
                                                      self._docker_pip_command,
                                                      package_tools_version))

        if self._conan_pip_package:
            commands.append("%s %s install %s --no-cache" % (self._sudo_pip_command,
                                                             self._docker_pip_command,
                                                              self._conan_pip_package))
        else:
            commands.append("%s %s install conan --upgrade --no-cache" % (self._sudo_pip_command,
                                                                          self._docker_pip_command))

        if self._pip_install:
            commands.append("%s %s install %s --upgrade --no-cache" % (self._sudo_pip_command,
                                                                       self._docker_pip_command,
                                                                       " ".join(self._pip_install)))

        command = " && ".join(commands)
        return command

    @staticmethod
    def is_selinux_running():
        if tools.which("getenforce"):
            output = subprocess.check_output("getenforce", shell=True)
            return "Enforcing" in output.decode()
        return False

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
                                  ' %s %s %s "%s"' % (self._sudo_docker_command,
                                                   env_vars_text,
                                                   self._docker_run_options,
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
        volume_options = ":z" if (DockerCreateRunner.is_selinux_running() or self._force_selinux) else ""

        command = ('%s docker run --rm -v "%s:%s/project%s" %s %s %s %s %s '
                   '"%s cd project && '
                   '%s run_create_in_docker "' % (self._sudo_docker_command,
                                                  self._cwd,
                                                  self._docker_conan_home,
                                                  volume_options,
                                                  env_vars_text,
                                                  self._docker_run_options,
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
            for retry in range(1, 4):
                ret = self._runner("%s docker pull %s" % (self._sudo_docker_command, self._docker_image))
                if ret == 0:
                    break
                elif retry == 3:
                    raise Exception("Error pulling the image: %s" % self._docker_image)
                self.printer.print_message("Could not pull docker image '{}'. Retry ({})"
                                           .format(self._docker_image, retry))
                time.sleep(3)

    def get_env_vars(self):
        ret = {key: value for key, value in os.environ.items() if key.startswith("CONAN_") and
               key != "CONAN_USER_HOME"}
        ret["CONAN_REFERENCE"] = self._reference

        ret["CPT_PROFILE"] = escape_env(self._profile_text)
        ret["CPT_BASE_PROFILE"] = escape_env(self._base_profile_text)
        ret["CPT_BASE_PROFILE_NAME"] = escape_env(self._base_profile_name)
        ret["CPT_PROFILE_BUILD"] = escape_env(self._profile_build_text)

        ret["CONAN_USERNAME"] = escape_env(self._reference.user or ret.get("CONAN_USERNAME"))
        ret["CONAN_TEMP_TEST_FOLDER"] = "1"  # test package folder to a temp one
        ret["CPT_UPLOAD_ENABLED"] = self._upload
        ret["CPT_UPLOAD_RETRY"] = self._upload_retry
        ret["CPT_UPLOAD_ONLY_RECIPE"] = self._upload_only_recipe
        ret["CPT_UPLOAD_FORCE"] = self._upload_force
        ret["CPT_BUILD_POLICY"] = escape_env(self._build_policy)
        ret["CPT_REQUIRE_OVERRIDES"] = escape_env(self._require_overrides)
        ret["CPT_TEST_FOLDER"] = escape_env(self._test_folder)
        ret["CPT_CONFIG_URL"] = escape_env(self._config_url)
        ret["CPT_CONFIG_ARGS"] = escape_env(self._config_args)
        ret["CPT_UPLOAD_DEPENDENCIES"] = escape_env(self._upload_dependencies)
        ret["CPT_CONANFILE"] = escape_env(self._conanfile)
        ret["CPT_LOCKFILE"] = escape_env(self._lockfile)
        ret["CPT_SKIP_RECIPE_EXPORT"] = self._skip_recipe_export
        ret["CPT_UPDATE_DEPENDENCIES"] = self._update_dependencies

        ret.update({key: value for key, value in os.environ.items() if key.startswith("PIP_")})

        return ret


def unscape_env(text):
    if not text:
        return text
    return text.replace("@@", "\n").replace('||', '"')


def escape_env(text):
    if not text:
        return text
    return text.replace("\r", "").replace("\n", "@@").replace('"', '||')


class PrintRunner(object):

    def __init__(self, runner, printer):
        self.runner = runner
        self.printer = printer

    def __call__(self, command, hide_sensitive=True):
        cmd_str = command
        if hide_sensitive:
            cmd_str = re.sub(r'(CONAN_LOGIN_USERNAME[_\w+]*)=\"(\w+)\"', r'\1="xxxxxxxx"', cmd_str)
            cmd_str = re.sub(r'(CONAN_PASSWORD[_\w+]*)=\"(\w+)\"', r'\1="xxxxxxxx"', cmd_str)
        self.printer.print_command(cmd_str)
        sys.stderr.flush()
        sys.stdout.flush()
        return self.runner(command)
