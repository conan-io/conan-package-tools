import os
import platform
import re
import sys
from collections import defaultdict

import six

from conans.client.loader_parse import load_conanfile_class
from conans.model.version import Version
from cpt.auth import AuthManager
from cpt.ci_manager import CIManager
from cpt.printer import Printer
from cpt.profiles import get_profiles, save_profile_to_tmp
from cpt.remotes import RemotesManager
from cpt.tools import get_bool_from_env
from cpt.builds_generator import BuildConf, BuildGenerator
from cpt.runner import CreateRunner, DockerCreateRunner
from conans.client.conan_api import Conan
from conans.client.runner import ConanRunner
from conans.model.ref import ConanFileReference
from conans import __version__ as client_version, tools
from cpt.uploader import Uploader


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

    def __init__(self, args=None, username=None, channel=None, runner=None,
                 gcc_versions=None, visual_versions=None, visual_runtimes=None,
                 apple_clang_versions=None, archs=None,
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
                 build_types=None,
                 skip_check_credentials=False,
                 allow_gcc_minors=False,
                 exclude_vcvars_precommand=False,
                 docker_image_skip_update=False,
                 docker_image_skip_pull=False,
                 docker_entry_script=None,
                 docker_32_images=None,
                 build_policy=None,
                 always_update_conan_in_docker=False,
                 conan_api=None,
                 client_cache=None,
                 ci_manager=None,
                 out=None,
                 test_folder=None):

        self.printer = Printer(out)
        self.printer.print_rule()
        self.printer.print_ascci_art()

        if not conan_api:
            self.conan_api, self.client_cache, _ = Conan.factory()
        else:
            self.conan_api = conan_api
            self.client_cache = client_cache

        self.ci_manager = ci_manager or CIManager(self.printer)
        self.remotes_manager = RemotesManager(self.conan_api, self.printer, remotes, upload)
        self.username = username or os.getenv("CONAN_USERNAME", None)

        if not self.username:
            raise Exception("Instance ConanMultiPackage with 'username' parameter or use "
                            "CONAN_USERNAME env variable")
        self.skip_check_credentials = skip_check_credentials or \
                                      os.getenv("CONAN_SKIP_CHECK_CREDENTIALS", False)

        self.auth_manager = AuthManager(self.conan_api, self.printer, login_username, password,
                                        default_username=self.username,
                                        skip_check_credentials=self.skip_check_credentials)

        # Upload related variables
        self.upload_retry = upload_retry or os.getenv("CONAN_UPLOAD_RETRY", 3)

        if upload_only_when_stable is not None:
            self.upload_only_when_stable = upload_only_when_stable
        else:
            self.upload_only_when_stable = get_bool_from_env("CONAN_UPLOAD_ONLY_WHEN_STABLE")

        self.uploader = Uploader(self.conan_api, self.remotes_manager, self.auth_manager,
                                 self.printer, self.upload_retry)

        self._builds = []
        self._named_builds = {}

        self._update_conan_in_docker = (always_update_conan_in_docker or
                                        os.getenv("CONAN_ALWAYS_UPDATE_CONAN_DOCKER", False))

        self._platform_info = platform_info or PlatformInfo()

        self.stable_branch_pattern = stable_branch_pattern or \
                                     os.getenv("CONAN_STABLE_BRANCH_PATTERN", None)
        self.specified_channel = channel or os.getenv("CONAN_CHANNEL", "testing")
        self.specified_channel = self.specified_channel.rstrip()
        self.stable_channel = stable_channel or os.getenv("CONAN_STABLE_CHANNEL", "stable")
        self.stable_channel = self.stable_channel.rstrip()
        self.channel = self._get_channel(self.specified_channel, self.stable_channel)
        self.partial_reference = reference or os.getenv("CONAN_REFERENCE", None)

        if self.partial_reference:
            if "@" in self.partial_reference:
                self.reference = ConanFileReference.loads(self.partial_reference)
            else:
                name, version = self.partial_reference.split("/")
                self.reference = ConanFileReference(name, version, self.username, self.channel)
        else:
            if not os.path.exists("conanfile.py"):
                raise Exception("Conanfile not found, specify a 'reference' parameter with name and version")
            conanfile = load_conanfile_class("./conanfile.py")
            name, version = conanfile.name, conanfile.version
            if name and version:
                self.reference = ConanFileReference(name, version, self.username, self.channel)
            else:
                self.reference = None

        # If CONAN_DOCKER_IMAGE is speified, then use docker is True
        self.use_docker = (use_docker or os.getenv("CONAN_USE_DOCKER", False) or
                           os.getenv("CONAN_DOCKER_IMAGE", None) is not None)

        os_name = self._platform_info.system() if not self.use_docker else "Linux"
        self.build_generator = BuildGenerator(reference, os_name, gcc_versions,
                                              apple_clang_versions, clang_versions,
                                              visual_versions, visual_runtimes, vs10_x86_64_enabled,
                                              mingw_configurations, archs, allow_gcc_minors,
                                              build_types)

        build_policy = (build_policy or
                        self.ci_manager.get_commit_build_policy() or
                        os.getenv("CONAN_BUILD_POLICY", None))

        if build_policy:
            if build_policy.lower() not in ("never", "outdated", "missing"):
                raise Exception("Invalid build policy, valid values: never, outdated, missing")

        self.build_policy = build_policy

        self.sudo_docker_command = ""
        if "CONAN_DOCKER_USE_SUDO" in os.environ:
            self.sudo_docker_command = "sudo -E" if get_bool_from_env("CONAN_DOCKER_USE_SUDO") else ""
        elif platform.system() != "Windows":
            self.sudo_docker_command = "sudo -E"

        self.sudo_pip_command = ""
        if "CONAN_PIP_USE_SUDO" in os.environ:
            self.sudo_pip_command = "sudo -E" if get_bool_from_env("CONAN_PIP_USE_SUDO") else ""
        elif platform.system() != "Windows":
            self.sudo_pip_command = "sudo -E"

        self.docker_shell = ""
        self.docker_conan_home = ""

        if self.is_wcow:
            self.docker_conan_home = "C:/Users/ContainerAdministrator"
            self.docker_shell = "cmd /C"
        else:
            self.docker_conan_home = "/home/conan"
            self.docker_shell = "/bin/sh -c"

        self.docker_platform_param = ""
        self.lcow_user_workaround = ""

        if self.is_lcow:
            self.docker_platform_param = "--platform=linux"
            # With LCOW, Docker doesn't respect USER directive in dockerfile yet
            self.lcow_user_workaround = "sudo su conan && "

        self.exclude_vcvars_precommand = (exclude_vcvars_precommand or
                                          os.getenv("CONAN_EXCLUDE_VCVARS_PRECOMMAND", False))
        self._docker_image_skip_update = (docker_image_skip_update or
                                          os.getenv("CONAN_DOCKER_IMAGE_SKIP_UPDATE", False))
        self._docker_image_skip_pull = (docker_image_skip_pull or
                                        os.getenv("CONAN_DOCKER_IMAGE_SKIP_PULL", False))

        self.runner = runner or os.system
        self.output_runner = ConanOutputRunner()
        self.args = " ".join(args) if args else " ".join(sys.argv[1:])

        self.docker_entry_script = docker_entry_script or os.getenv("CONAN_DOCKER_ENTRY_SCRIPT")

        os.environ["CONAN_CHANNEL"] = self.channel

        # If CONAN_DOCKER_IMAGE is speified, then use docker is True
        self.use_docker = use_docker or os.getenv("CONAN_USE_DOCKER", False) or \
                          (os.getenv("CONAN_DOCKER_IMAGE", None) is not None)

        if docker_32_images is not None:
            self.docker_32_images = docker_32_images
        else:
            self.docker_32_images = os.getenv("CONAN_DOCKER_32_IMAGES", False)

        self.curpage = curpage or os.getenv("CONAN_CURRENT_PAGE", 1)
        self.total_pages = total_pages or os.getenv("CONAN_TOTAL_PAGES", 1)
        self._docker_image = docker_image or os.getenv("CONAN_DOCKER_IMAGE", None)

        self.conan_pip_package = os.getenv("CONAN_PIP_PACKAGE", "conan==%s" % client_version)
        if self.conan_pip_package in ("0", "False"):
            self.conan_pip_package = False
        self.vs10_x86_64_enabled = vs10_x86_64_enabled

        self.builds_in_current_page = []

        self.test_folder = test_folder or os.getenv("CPT_TEST_FOLDER", None)

        def valid_pair(var, value):
            return (isinstance(value, six.string_types) or
                    isinstance(value, bool) or
                    isinstance(value, list)) and not var.startswith("_") and "password" not in var
        with self.printer.foldable_output("local_vars"):
            self.printer.print_dict({var: value
                                     for var, value in self.__dict__.items()
                                     if valid_pair(var, value)})

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

    def add_common_builds(self, shared_option_name=None, pure_c=True,
                          dll_with_static_runtime=False, reference=None):

        if not reference and not self.reference:
            raise Exception("Specify a CONAN_REFERENCE or name and version fields in the recipe")

        if shared_option_name is None:
            if os.path.exists("conanfile.py"):
                conanfile = load_conanfile_class("./conanfile.py")
                if hasattr(conanfile, "options") and "shared" in conanfile.options:
                    shared_option_name = "%s:shared" % self.reference.name

        tmp = self.build_generator.get_builds(pure_c, shared_option_name, dll_with_static_runtime,
                                              reference or self.reference)
        self._builds.extend(tmp)

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

    def run(self, base_profile_name=None):
        env_vars = self.auth_manager.env_vars()
        env_vars.update(self.remotes_manager.env_vars())
        with tools.environment_append(env_vars):
            self.printer.print_message("Running builds...")
            if self.ci_manager.skip_builds():
                print("Skipped builds due [skip ci] commit message")
                return 99
            if not self.skip_check_credentials and self._upload_enabled():
                self.remotes_manager.add_remotes_to_conan()
                self.auth_manager.login(self.remotes_manager.upload_remote_name)
            if self.conan_pip_package and not self.use_docker:
                with self.printer.foldable_output("pip_update"):
                    self.runner('%s pip install %s' % (self.sudo_pip_command,
                                                       self.conan_pip_package))

            self.run_builds(base_profile_name=base_profile_name)

    def _upload_enabled(self):
        if not self.remotes_manager.upload_remote_name:
            return False

        if not self.auth_manager.credentials_ready(self.remotes_manager.upload_remote_name):
            return False

        st_channel = self.stable_channel or "stable"
        if self.upload_only_when_stable and self.channel != st_channel:
            self.printer.print_message("Skipping upload, not stable channel")
            return False

        if not os.getenv("CONAN_TEST_SUITE", False):
            if self.ci_manager.is_pull_request():
                # PENDING! can't found info for gitlab/bamboo
                self.printer.print_message("Skipping upload, this is a Pull Request")
                return False

        def raise_error(field):
            raise Exception("Upload not possible, '%s' is missing!" % field)

        if not self.channel:
            raise_error("channel")
        if not self.username:
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

        # FIXME: Remove in Conan 1.3, https://github.com/conan-io/conan/issues/2787
        abs_folder = os.path.realpath(os.getcwd())
        for build in self.builds_in_current_page:
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
                                 args=self.args,
                                 exclude_vcvars_precommand=self.exclude_vcvars_precommand,
                                 build_policy=self.build_policy,
                                 runner=self.runner,
                                 abs_folder=abs_folder,
                                 printer=self.printer,
                                 upload=self._upload_enabled(),
                                 test_folder=self.test_folder)
                r.run()
            else:
                docker_image = self._get_docker_image(build)
                r = DockerCreateRunner(profile_text, base_profile_text, base_profile_name,
                                       build.reference, args=self.args,
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
                                       runner=self.runner,
                                       docker_shell=self.docker_shell,
                                       docker_conan_home=self.docker_conan_home,
                                       docker_platform_param=self.docker_platform_param,
                                       lcow_user_workaround=self.lcow_user_workaround,
                                       test_folder=self.test_folder)

                r.run(pull_image=not pulled_docker_images[docker_image],
                      docker_entry_script=self.docker_entry_script)
                pulled_docker_images[docker_image] = True

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

        return "lasote/conan%s%s" % (compiler_name, compiler_version.replace(".", ""))

    def _get_channel(self, specified_channel, stable_channel):
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

        return specified_channel
