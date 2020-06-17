import os
import platform
import re
import sys
import copy
from collections import defaultdict
from itertools import product

import six
from conans import tools
from conans.client.conan_api import Conan
from conans.client.runner import ConanRunner
from conans.model.ref import ConanFileReference
from conans.model.version import Version

from cpt import NEWEST_CONAN_SUPPORTED, get_client_version
from cpt.auth import AuthManager
from cpt.builds_generator import BuildConf, BuildGenerator
from cpt.ci_manager import CIManager
from cpt.printer import Printer
from cpt.profiles import get_profiles, save_profile_to_tmp
from cpt.remotes import RemotesManager
from cpt.runner import CreateRunner, DockerCreateRunner
from cpt.tools import get_bool_from_env
from cpt.tools import split_colon_env
from cpt.uploader import Uploader


def load_cf_class(path, conan_api):
    client_version = get_client_version()
    client_version = Version(client_version)
    if client_version < Version("1.7.0"):
        from conans.client.loader_parse import load_conanfile_class
        return load_conanfile_class(path)
    elif client_version < Version("1.14.0"):
        return conan_api._loader.load_class(path)
    elif client_version < Version("1.15.0"):
        remotes = conan_api._cache.registry.remotes.list
        for remote in remotes:
            conan_api.python_requires.enable_remotes(remote_name=remote)
        return conan_api._loader.load_class(path)
    elif client_version < Version("1.16.0"):
        remotes = conan_api._cache.registry.load_remotes()
        conan_api.python_requires.enable_remotes(remotes=remotes)
        return conan_api._loader.load_class(path)
    elif client_version < Version("1.18.0"):
        remotes = conan_api._cache.registry.load_remotes()
        conan_api._python_requires.enable_remotes(remotes=remotes)
        return conan_api._loader.load_class(path)
    else:
        if not conan_api.app:
            conan_api.create_app()
        remotes = conan_api.app.cache.registry.load_remotes()
        conan_api.app.python_requires.enable_remotes(remotes=remotes)
        conan_api.app.pyreq_loader.enable_remotes(remotes=remotes)
        if client_version < Version("1.20.0"):
            return conan_api.app.loader.load_class(path)
        elif client_version < Version("1.21.0"):
            return conan_api.app.loader.load_basic(path)
        else:
            return conan_api.app.loader.load_named(path, None, None, None, None)


class PlatformInfo(object):
    """Easy mockable for testing"""
    @staticmethod
    def system():
        import platform
        return platform.system()


class ConanOutputRunner(ConanRunner):

    def __init__(self):
        super(ConanOutputRunner, self).__init__()

        class OutputInternal(object):
            def __init__(self):
                self.output = ""

            def write(self, data):
                self.output += str(data)
                sys.stdout.write(data)

        self._output = OutputInternal()

    @property
    def output(self):
        return self._output.output

    def __call__(self, command):
        return super(ConanOutputRunner, self).__call__(command, output=self._output)


class ConanMultiPackager(object):
    """ Help to generate common builds (setting's combinations), adjust the environment,
    and run conan create command in docker containers"""

    def __init__(self, username=None, channel=None, runner=None,
                 gcc_versions=None, visual_versions=None, visual_runtimes=None,
                 visual_toolsets=None,
                 apple_clang_versions=None, archs=None, options=None,
                 use_docker=None, curpage=None, total_pages=None,
                 docker_image=None, reference=None, password=None,
                 remotes=None,
                 upload=None, stable_branch_pattern=None,
                 vs10_x86_64_enabled=False,
                 mingw_configurations=None,
                 stable_channel=None,
                 platform_info=None,
                 upload_retry=None,
                 clang_versions=None,
                 login_username=None,
                 upload_only_when_stable=None,
                 upload_only_when_tag=None,
                 upload_only_recipe=None,
                 build_types=None,
                 cppstds=None,
                 skip_check_credentials=False,
                 allow_gcc_minors=False,
                 exclude_vcvars_precommand=False,
                 docker_run_options=None,
                 docker_image_skip_update=False,
                 docker_image_skip_pull=False,
                 docker_entry_script=None,
                 docker_32_images=None,
                 docker_conan_home=None,
                 docker_shell=None,
                 pip_install=None,
                 build_policy=None,
                 always_update_conan_in_docker=False,
                 conan_api=None,
                 client_cache=None,
                 conanfile=None,
                 ci_manager=None,
                 out=None,
                 test_folder=None,
                 cwd=None,
                 config_url=None,
                 config_args=None,
                 upload_dependencies=None,
                 force_selinux=None,
                 skip_recipe_export=False,
                 update_dependencies=None,
                 lockfile=None):

        conan_version = get_client_version()

        self.printer = Printer(out)
        self.printer.print_rule()
        self.printer.print_ascci_art()

        self.cwd = cwd or os.getcwd()

        if not conan_api:
            self.conan_api, _, _ = Conan.factory()
            self.conan_api.create_app()
            self.client_cache = self.conan_api.app.cache
        else:
            self.conan_api = conan_api
            self.client_cache = client_cache

        self.ci_manager = ci_manager or CIManager(self.printer)
        self.remotes_manager = RemotesManager(self.conan_api, self.printer, remotes, upload)
        self.username = username or os.getenv("CONAN_USERNAME", None)

        self.skip_check_credentials = skip_check_credentials or get_bool_from_env("CONAN_SKIP_CHECK_CREDENTIALS")

        self.auth_manager = AuthManager(self.conan_api, self.printer, login_username, password,
                                        default_username=self.username,
                                        skip_check_credentials=self.skip_check_credentials)

        # Upload related variables
        self.upload_retry = upload_retry or os.getenv("CONAN_UPLOAD_RETRY", 3)

        if upload_only_when_stable is not None:
            self.upload_only_when_stable = upload_only_when_stable
        else:
            self.upload_only_when_stable = get_bool_from_env("CONAN_UPLOAD_ONLY_WHEN_STABLE")

        if upload_only_when_tag is not None:
            self.upload_only_when_tag = upload_only_when_tag
        else:
            self.upload_only_when_tag = get_bool_from_env("CONAN_UPLOAD_ONLY_WHEN_TAG")

        self.upload_only_recipe = upload_only_recipe or get_bool_from_env("CONAN_UPLOAD_ONLY_RECIPE")

        self.remotes_manager.add_remotes_to_conan()
        self.uploader = Uploader(self.conan_api, self.remotes_manager, self.auth_manager,
                                 self.printer, self.upload_retry)

        self._builds = []
        self._named_builds = {}
        self._packages_summary = []

        self._update_conan_in_docker = always_update_conan_in_docker or get_bool_from_env("CONAN_ALWAYS_UPDATE_CONAN_DOCKER")

        self._platform_info = platform_info or PlatformInfo()

        self.stable_branch_pattern = stable_branch_pattern or \
                                     os.getenv("CONAN_STABLE_BRANCH_PATTERN", None)

        self.stable_channel = stable_channel or os.getenv("CONAN_STABLE_CHANNEL", "stable")
        self.stable_channel = self.stable_channel.rstrip()
        self.partial_reference = reference or os.getenv("CONAN_REFERENCE", None)
        self.channel = self._get_specified_channel(channel, reference)
        self.conanfile = conanfile or os.getenv("CONAN_CONANFILE", "conanfile.py")

        if self.partial_reference:
            if "@" in self.partial_reference:
                self.reference = ConanFileReference.loads(self.partial_reference)
            else:
                name, version = self.partial_reference.split("/")
                self.reference = ConanFileReference(name, version, self.username, self.channel)
        else:
            if not os.path.exists(os.path.join(self.cwd, self.conanfile)):
                raise Exception("Conanfile not found, specify a 'reference' "
                                "parameter with name and version")

            conanfile = load_cf_class(os.path.join(self.cwd, self.conanfile), self.conan_api)
            name, version = conanfile.name, conanfile.version
            if name and version:
                self.reference = ConanFileReference(name, version, self.username, self.channel)
            else:
                self.reference = None

        self._docker_image = docker_image or os.getenv("CONAN_DOCKER_IMAGE", None)

        # If CONAN_DOCKER_IMAGE is specified, then use docker is True
        self.use_docker = (use_docker or os.getenv("CONAN_USE_DOCKER", False) or
                           self._docker_image is not None)

        self.docker_conan_home = docker_conan_home or os.getenv("CONAN_DOCKER_HOME", None)

        os_name = self._platform_info.system() if not self.use_docker else "Linux"
        self.build_generator = BuildGenerator(reference, os_name, gcc_versions,
                                              apple_clang_versions, clang_versions,
                                              visual_versions, visual_runtimes, visual_toolsets,
                                              vs10_x86_64_enabled,
                                              mingw_configurations, archs, allow_gcc_minors,
                                              build_types, options, cppstds)

        self.build_policy = (build_policy or
                        self.ci_manager.get_commit_build_policy() or
                        split_colon_env("CONAN_BUILD_POLICY"))
        if isinstance(self.build_policy, list):
            self.build_policy = ",".join(self.build_policy)

        self.sudo_docker_command = ""
        if "CONAN_DOCKER_USE_SUDO" in os.environ:
            self.sudo_docker_command = "sudo -E" if get_bool_from_env("CONAN_DOCKER_USE_SUDO") else ""
        elif platform.system() != "Windows":
            self.sudo_docker_command = "sudo -E"

        self.sudo_pip_command = ""
        if "CONAN_PIP_USE_SUDO" in os.environ:
            self.sudo_pip_command = "sudo -E" if get_bool_from_env("CONAN_PIP_USE_SUDO") else ""
        elif platform.system() != "Windows" and self._docker_image and 'conanio/' not in str(self._docker_image):
            self.sudo_pip_command = "sudo -E"
        self.pip_command = os.getenv("CONAN_PIP_COMMAND", "pip")
        pip_found = True if tools.os_info.is_windows else tools.which(self.pip_command)
        if not pip_found or not "pip" in self.pip_command:
            raise Exception("CONAN_PIP_COMMAND: '{}' is not a valid pip command.".format(self.pip_command))
        self.docker_pip_command = os.getenv("CONAN_DOCKER_PIP_COMMAND", "pip")

        self.docker_shell = docker_shell or os.getenv("CONAN_DOCKER_SHELL")

        if self.is_wcow:
            if self.docker_conan_home is None:
                self.docker_conan_home = "C:/Users/ContainerAdministrator"
                self.docker_shell = docker_shell or "cmd /C"
        else:
            if self.docker_conan_home is None:
                self.docker_conan_home = "/home/conan"
                self.docker_shell = docker_shell or "/bin/sh -c"

        self.docker_platform_param = ""
        self.lcow_user_workaround = ""

        if self.is_lcow:
            self.docker_platform_param = "--platform=linux"
            # With LCOW, Docker doesn't respect USER directive in dockerfile yet
            self.lcow_user_workaround = "sudo su conan && "

        self.exclude_vcvars_precommand = exclude_vcvars_precommand or \
                                          get_bool_from_env("CONAN_EXCLUDE_VCVARS_PRECOMMAND")
        self._docker_image_skip_update = docker_image_skip_update or \
                                          get_bool_from_env("CONAN_DOCKER_IMAGE_SKIP_UPDATE")
        self._docker_image_skip_pull = docker_image_skip_pull or \
                                        get_bool_from_env("CONAN_DOCKER_IMAGE_SKIP_PULL")

        self.runner = runner or os.system
        self.output_runner = ConanOutputRunner()

        self.docker_run_options = docker_run_options or split_colon_env("CONAN_DOCKER_RUN_OPTIONS")
        if isinstance(self.docker_run_options, list):
            self.docker_run_options = " ".join(self.docker_run_options)

        self.docker_entry_script = docker_entry_script or os.getenv("CONAN_DOCKER_ENTRY_SCRIPT")

        self.pip_install = pip_install or split_colon_env("CONAN_PIP_INSTALL")

        self.upload_dependencies = upload_dependencies or split_colon_env("CONAN_UPLOAD_DEPENDENCIES") or ""
        if isinstance(self.upload_dependencies, list):
            self.upload_dependencies = ",".join(self.upload_dependencies)
        if "all" in self.upload_dependencies and self.upload_dependencies != "all":
            raise Exception("Upload dependencies only accepts or 'all' or package references. Do not mix both!")

        self.update_dependencies = update_dependencies or get_bool_from_env("CONAN_UPDATE_DEPENDENCIES")

        if self.channel:
            os.environ["CONAN_CHANNEL"] = self.channel

        if docker_32_images is not None:
            self.docker_32_images = docker_32_images
        else:
            self.docker_32_images = os.getenv("CONAN_DOCKER_32_IMAGES", False)

        self.force_selinux = force_selinux or get_bool_from_env("CONAN_FORCE_SELINUX")
        self.curpage = curpage or os.getenv("CONAN_CURRENT_PAGE", 1)
        self.total_pages = total_pages or os.getenv("CONAN_TOTAL_PAGES", 1)

        self.conan_pip_package = os.getenv("CONAN_PIP_PACKAGE", "conan==%s" % conan_version)
        if self.conan_pip_package in ("0", "False"):
            self.conan_pip_package = ""
        self.vs10_x86_64_enabled = vs10_x86_64_enabled

        self.builds_in_current_page = []

        self.test_folder = test_folder or os.getenv("CPT_TEST_FOLDER")

        self.config_url = config_url or os.getenv("CONAN_CONFIG_URL")

        self.skip_recipe_export = skip_recipe_export or \
                                     get_bool_from_env("CONAN_SKIP_RECIPE_EXPORT")
        self.config_args = config_args or os.getenv("CONAN_CONFIG_ARGS")

        self.lockfile = lockfile or os.getenv("CONAN_LOCKFILE")

        def valid_pair(var, value):
            return (isinstance(value, six.string_types) or
                    isinstance(value, bool) or
                    isinstance(value, list)) and not var.startswith("_") and "password" not in var
        with self.printer.foldable_output("local_vars"):
            self.printer.print_dict({var: value
                                     for var, value in self.__dict__.items()
                                     if valid_pair(var, value)})

        self._newest_supported_conan_version = Version(NEWEST_CONAN_SUPPORTED).minor(fill=False)
        self._client_conan_version = conan_version

    def _check_conan_version(self):
        tmp = self._newest_supported_conan_version
        if Version(self._client_conan_version).minor(fill=False) > tmp:
            msg = "Conan/CPT version mismatch. Conan version installed: " \
                  "%s . This version of CPT supports only Conan < %s" \
                  "" % (self._client_conan_version, str(tmp))
            self.printer.print_message(msg)
            raise Exception(msg)

    # For Docker on Windows, including Linux containers on Windows
    @property
    def is_lcow(self):
        return self.container_os == "linux" and platform.system() == "Windows"

    @property
    def is_wcow(self):
        return self.container_os == "windows" and platform.system() == "Windows"

    @property
    def container_os(self):
        # CONAN_DOCKER_PLATFORM=linux must be specified for LCOW
        if self.use_docker:
            if "CONAN_DOCKER_PLATFORM" in os.environ:
                return os.getenv("CONAN_DOCKER_PLATFORM", "windows").lower()
            else:
                return "windows"
        else:
            return ""

    @property
    def packages_summary(self):
        return self._packages_summary

    def save_packages_summary(self, file):
        self.printer.print_message("Saving packages summary to " + file)
        import json
        import datetime
        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()

        with open(file, 'w') as outfile:
            json.dump(self.packages_summary, outfile, default = default)

    @property
    def items(self):
        return self._builds

    @items.setter
    def items(self, confs):
        self.builds = confs

    @property
    def builds(self):
        # Retrocompatibility iterating
        self.printer.print_message("WARNING",
                                   "\n\n\n******* ITERATING THE CONAN_PACKAGE_TOOLS BUILDS WITH "
                                   ".builds is deprecated use '.items' instead (unpack 5 elements: "
                                   "settings, options, env_vars, build_requires, reference  *******"
                                   "**\n\n\n")
        return [elem[0:4] for elem in self._builds]

    @builds.setter
    def builds(self, confs):
        """For retro compatibility directly assigning builds"""
        self._named_builds = {}
        self._builds = []
        for values in confs:
            if len(values) == 2:
                self._builds.append(BuildConf(values[0], values[1], {}, {}, self.reference))
            elif len(values) == 4:
                self._builds.append(BuildConf(values[0], values[1], values[2], values[3],
                                              self.reference))
            elif len(values) != 5:
                raise Exception("Invalid build configuration, has to be a tuple of "
                                "(settings, options, env_vars, build_requires, reference)")
            else:
                self._builds.append(BuildConf(*values))

    @property
    def named_builds(self):
        return self._named_builds

    @named_builds.setter
    def named_builds(self, confs):
        self._builds = []
        self._named_builds = {}
        for key, pages in confs.items():
            for values in pages:
                if len(values) == 2:
                    bc = BuildConf(values[0], values[1], {}, {}, self.reference)
                    self._named_builds.setdefault(key, []).append(bc)
                elif len(values) == 4:
                    bc = BuildConf(values[0], values[1], values[2], values[3], self.reference)
                    self._named_builds.setdefault(key, []).append(bc)
                elif len(values) != 5:
                    raise Exception("Invalid build configuration, has to be a tuple of "
                                    "(settings, options, env_vars, build_requires, reference)")
                else:
                    self._named_builds.setdefault(key, []).append(BuildConf(*values))

    def login(self, remote_name):
        self.auth_manager.login(remote_name)

    def add_common_builds(self, shared_option_name=None, pure_c=True,
                          dll_with_static_runtime=False, reference=None, header_only=True,
                          build_all_options_values=None):
        if reference:
            if "@" in reference:
                reference = ConanFileReference.loads(reference)
            else:
                name, version = reference.split("/")
                reference = ConanFileReference(name, version, self.username, self.channel)
        else:
            reference = self.reference

        if not reference:
            raise Exception("Specify a CONAN_REFERENCE or name and version fields in the recipe")

        if shared_option_name is None:
            env_shared_option_name = os.getenv("CONAN_SHARED_OPTION_NAME", None)
            shared_option_name = env_shared_option_name if str(env_shared_option_name).lower() != "false" else False

        build_all_options_values = build_all_options_values or split_colon_env("CONAN_BUILD_ALL_OPTIONS_VALUES") or []
        if not isinstance(build_all_options_values, list):
            raise Exception("'build_all_options_values' must be a list. e.g. ['foo:opt', 'foo:bar']")

        conanfile = None
        if os.path.exists(os.path.join(self.cwd, self.conanfile)):
            conanfile = load_cf_class(os.path.join(self.cwd, self.conanfile), self.conan_api)

        header_only_option = None
        if conanfile:
            if hasattr(conanfile, "options") and conanfile.options and "header_only" in conanfile.options:
                header_only_option = "%s:header_only" % reference.name

        if shared_option_name is None:
            if conanfile:
                if hasattr(conanfile, "options") and conanfile.options and "shared" in conanfile.options:
                    shared_option_name = "%s:shared" % reference.name

        # filter only valid options
        raw_options_for_building = [opt[opt.find(":") + 1:] for opt in build_all_options_values]
        for raw_option in reversed(raw_options_for_building):
            if hasattr(conanfile, "options") and conanfile.options and \
               not isinstance(conanfile.options.get(raw_option), list):
                raw_options_for_building.remove(raw_option)
        if raw_options_for_building and conanfile:
            # get option and its values
            cloned_options = copy.copy(conanfile.options)
            for key, value in conanfile.options.items():
                if key == "shared" and shared_option_name:
                    continue
                elif key not in raw_options_for_building:
                    del cloned_options[key]
            cloned_options2 = {}
            for key, value in cloned_options.items():
                # add package reference to the option name
                if not key.startswith("{}:".format(reference.name)):
                    cloned_options2["{}:{}".format(reference.name, key)] = value
            # combine all options x values (cartesian product)
            build_all_options_values = [dict(zip(cloned_options2, v)) for v in product(*cloned_options2.values())]

        builds = self.build_generator.get_builds(pure_c, shared_option_name,
                                                 dll_with_static_runtime, reference,
                                                 build_all_options_values)

        if header_only_option and header_only:
            if conanfile.default_options.get("header_only"):
                cloned_builds = copy.deepcopy(builds)
                for settings, options, env_vars, build_requires, reference in cloned_builds:
                    options.update({header_only_option: False})
                builds.extend(cloned_builds)
            else:
                settings, options, env_vars, build_requires, reference = builds[0]
                cloned_options = copy.copy(options)
                cloned_options.update({header_only_option: True})
                builds.append(BuildConf(copy.copy(settings), cloned_options, copy.copy(env_vars),
                                        copy.copy(build_requires), reference))

        self._builds.extend(builds)

    def add(self, settings=None, options=None, env_vars=None, build_requires=None, reference=None):
        settings = settings or {}
        options = options or {}
        env_vars = env_vars or {}
        build_requires = build_requires or {}
        if reference:
            reference = ConanFileReference.loads("%s@%s/%s" % (reference,
                                                               self.username, self.channel))
        reference = reference or self.reference
        self._builds.append(BuildConf(settings, options, env_vars, build_requires, reference))

    def remove_build_if(self, predicate):
        filtered_builds = []
        for build in self.items:
            if not predicate(build):
                filtered_builds.append(build)

        self._builds = filtered_builds

    def update_build_if(self, predicate, new_settings=None, new_options=None, new_env_vars=None,
                        new_build_requires=None, new_reference=None):
        updated_builds = []
        for build in self.items:
            if predicate(build):
                if new_settings:
                    build.settings.update(new_settings)
                if new_options:
                    build.options.update(new_options)
                if new_build_requires:
                    build.build_requires.update(new_build_requires)
                if new_env_vars:
                    build.env_vars.update(new_env_vars)
                if new_reference:
                    build.reference = new_reference
            updated_builds.append(build)
        self._builds = updated_builds

    def run(self, base_profile_name=None, summary_file=None):
        self._check_conan_version()

        env_vars = self.auth_manager.env_vars()
        env_vars.update(self.remotes_manager.env_vars())
        with tools.environment_append(env_vars):
            self.printer.print_message("Running builds...")
            if self.ci_manager.skip_builds():
                self.printer.print_message("Skipped builds due [skip ci] commit message")
                return 99
            if not self.skip_check_credentials and self._upload_enabled():
                self.auth_manager.login(self.remotes_manager.upload_remote_name)
            if self.conan_pip_package and not self.use_docker:
                with self.printer.foldable_output("pip_update"):
                    self.runner('%s %s install -q %s' % (self.sudo_pip_command,
                                                      self.pip_command,
                                                      self.conan_pip_package))
                    if self.pip_install:
                        packages = " ".join(self.pip_install)
                        self.printer.print_message("Install extra python packages: {}".format(packages))
                        self.runner('%s %s install -q %s' % (self.sudo_pip_command,
                                                          self.pip_command, packages))

            self.run_builds(base_profile_name=base_profile_name)

        summary_file = summary_file or os.getenv("CPT_SUMMARY_FILE", None)
        if summary_file:
            self.save_packages_summary(summary_file)

    def _upload_enabled(self):
        if not self.remotes_manager.upload_remote_name:
            return False

        if not self.auth_manager.credentials_ready(self.remotes_manager.upload_remote_name):
            return False

        if self.upload_only_when_tag and not self.ci_manager.is_tag():
            self.printer.print_message("Skipping upload, not tag branch")
            return False

        st_channel = self.stable_channel or "stable"
        if self.upload_only_when_stable and self.channel != st_channel and not self.upload_only_when_tag:
            self.printer.print_message("Skipping upload, not stable channel")
            return False

        if not os.getenv("CONAN_TEST_SUITE", False):
            if self.ci_manager.is_pull_request():
                # PENDING! can't found info for gitlab/bamboo
                self.printer.print_message("Skipping upload, this is a Pull Request")
                return False

        def raise_error(field):
            raise Exception("Upload not possible, '%s' is missing!" % field)

        if not self.channel and "@" not in self.partial_reference:
            raise_error("channel")
        if not self.username and "@" not in self.partial_reference:
            raise_error("username")

        return True

    def run_builds(self, curpage=None, total_pages=None, base_profile_name=None):
        if len(self.named_builds) > 0 and len(self.items) > 0:
            raise Exception("Both bulk and named builds are set. Only one is allowed.")

        self.builds_in_current_page = []
        if len(self.items) > 0:
            curpage = curpage or int(self.curpage)
            total_pages = total_pages or int(self.total_pages)
            for index, build in enumerate(self.items):
                if curpage is None or total_pages is None or (index % total_pages) + 1 == curpage:
                    self.builds_in_current_page.append(build)
        elif len(self.named_builds) > 0:
            curpage = curpage or self.curpage
            if curpage not in self.named_builds:
                raise Exception("No builds set for page %s" % curpage)
            for build in self.named_builds[curpage]:
                self.builds_in_current_page.append(build)

        self.printer.print_current_page(curpage, total_pages)
        self.printer.print_jobs(self.builds_in_current_page)

        pulled_docker_images = defaultdict(lambda: False)
        skip_recipe_export = False

        # FIXME: Remove in Conan 1.3, https://github.com/conan-io/conan/issues/2787
        for index, build in enumerate(self.builds_in_current_page):
            self.printer.print_message("Build: %s/%s" % (index+1, len(self.builds_in_current_page)))
            base_profile_name = base_profile_name or os.getenv("CONAN_BASE_PROFILE")
            if base_profile_name:
                self.printer.print_message("**************************************************")
                self.printer.print_message("Using specified default "
                                           "base profile: %s" % base_profile_name)
                self.printer.print_message("**************************************************")

            profile_text, base_profile_text = get_profiles(self.client_cache, build,
                                                           base_profile_name)
            if not self.use_docker:
                profile_abs_path = save_profile_to_tmp(profile_text)
                r = CreateRunner(profile_abs_path, build.reference, self.conan_api,
                                 self.uploader,
                                 exclude_vcvars_precommand=self.exclude_vcvars_precommand,
                                 build_policy=self.build_policy,
                                 runner=self.runner,
                                 cwd=self.cwd,
                                 printer=self.printer,
                                 upload=self._upload_enabled(),
                                 upload_only_recipe=self.upload_only_recipe,
                                 test_folder=self.test_folder,
                                 config_url=self.config_url,
                                 config_args=self.config_args,
                                 upload_dependencies=self.upload_dependencies,
                                 conanfile=self.conanfile,
                                 lockfile=self.lockfile,
                                 skip_recipe_export=skip_recipe_export,
                                 update_dependencies=self.update_dependencies)
                r.run()
                self._packages_summary.append({"configuration":  build, "package" : r.results})
            else:
                docker_image = self._get_docker_image(build)
                r = DockerCreateRunner(profile_text, base_profile_text, base_profile_name,
                                       build.reference,
                                       conan_pip_package=self.conan_pip_package,
                                       docker_image=docker_image,
                                       sudo_docker_command=self.sudo_docker_command,
                                       sudo_pip_command=self.sudo_pip_command,
                                       docker_image_skip_update=self._docker_image_skip_update,
                                       docker_image_skip_pull=self._docker_image_skip_pull,
                                       build_policy=self.build_policy,
                                       always_update_conan_in_docker=self._update_conan_in_docker,
                                       upload=self._upload_enabled(),
                                       upload_retry=self.upload_retry,
                                       upload_only_recipe=self.upload_only_recipe,
                                       runner=self.runner,
                                       docker_shell=self.docker_shell,
                                       docker_conan_home=self.docker_conan_home,
                                       docker_platform_param=self.docker_platform_param,
                                       docker_run_options=self.docker_run_options,
                                       lcow_user_workaround=self.lcow_user_workaround,
                                       test_folder=self.test_folder,
                                       pip_install=self.pip_install,
                                       docker_pip_command=self.docker_pip_command,
                                       config_url=self.config_url,
                                       config_args=self.config_args,
                                       printer=self.printer,
                                       upload_dependencies=self.upload_dependencies,
                                       conanfile=self.conanfile,
                                       lockfile=self.lockfile,
                                       force_selinux=self.force_selinux,
                                       skip_recipe_export=skip_recipe_export,
                                       update_dependencies=self.update_dependencies)

                r.run(pull_image=not pulled_docker_images[docker_image],
                      docker_entry_script=self.docker_entry_script)
                pulled_docker_images[docker_image] = True

            skip_recipe_export = self.skip_recipe_export

    def _get_docker_image(self, build):
        if self._docker_image:
            docker_image = self._docker_image
        else:
            compiler_name = build.settings.get("compiler", "")
            compiler_version = build.settings.get("compiler.version", "")
            docker_image = self._autodetect_docker_base_image(compiler_name, compiler_version)

        arch = build.settings.get("arch", "") or build.settings.get("arch_build", "")
        if self.docker_32_images and arch == "x86":
            build.settings["arch_build"] = "x86"
            docker_arch_suffix = "x86"
        elif arch != "x86" and arch != "x86_64":
            docker_arch_suffix = arch
        else:
            docker_arch_suffix = None
        if docker_arch_suffix and "-" not in docker_image:
            docker_image = "%s-%s" % (docker_image, docker_arch_suffix)

        return docker_image

    @staticmethod
    def _autodetect_docker_base_image(compiler_name, compiler_version):
        if compiler_name not in ["clang", "gcc"]:
            raise Exception("Docker image cannot be autodetected for "
                            "the compiler %s" % compiler_name)

        if compiler_name == "gcc" and Version(compiler_version) > Version("5"):
            compiler_version = Version(compiler_version).major(fill=False)

        return "conanio/%s%s" % (compiler_name, compiler_version.replace(".", ""))

    def _get_channel(self, specified_channel, stable_channel, upload_when_tag):
        if not specified_channel:
            return

        if self.stable_branch_pattern:
            stable_patterns = [self.stable_branch_pattern]
        else:
            stable_patterns = ["master$", "release*", "stable*"]

        branch = self.ci_manager.get_branch()
        self.printer.print_message("Branch detected", branch)

        for pattern in stable_patterns:
            prog = re.compile(pattern)

            if branch and prog.match(branch):
                self.printer.print_message("Info",
                                           "Redefined channel by CI branch matching with '%s', "
                                           "setting CONAN_CHANNEL to '%s'" % (pattern,
                                                                              stable_channel))
                return stable_channel

        if self.ci_manager.is_tag() and upload_when_tag:
            self.printer.print_message("Info",
                                           "Redefined channel by branch tag, "
                                           "setting CONAN_CHANNEL to '%s'" % stable_channel)
            return stable_channel

        return specified_channel

    def _get_specified_channel(self, channel, reference):
        partial_reference = reference or os.getenv("CONAN_REFERENCE", None)
        specified_channel = None
        # without name/channel e.g. zlib/1.2.11@
        if partial_reference:
            if "@" in partial_reference:
                specified_channel = channel or os.getenv("CONAN_CHANNEL", None)
            else:
                specified_channel = channel or os.getenv("CONAN_CHANNEL", "testing")
                specified_channel = specified_channel.rstrip()
        else:
            if self.username:
                specified_channel = channel or os.getenv("CONAN_CHANNEL", "testing")
                specified_channel = specified_channel.rstrip()
            else:
                specified_channel = channel or os.getenv("CONAN_CHANNEL", None)
        return self._get_channel(specified_channel, self.stable_channel, self.upload_only_when_tag)
