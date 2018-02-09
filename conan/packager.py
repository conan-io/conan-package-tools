import os
import platform
import re
import sys
from collections import defaultdict

from conan.tools import get_bool_from_env
from conan.builds_generator import (get_linux_gcc_builds, get_linux_clang_builds, get_visual_builds,
                                    get_osx_apple_clang_builds, get_mingw_builds, BuildConf)
from conan.create_runner import TestPackageRunner, DockerTestPackageRunner
from conan.log import logger
from conans.client.conan_api import Conan
from conans.client.runner import ConanRunner
from conans.model.ref import ConanFileReference
from conans.model.version import Version
from conans import __version__ as client_version


def get_mingw_config_from_env():
    tmp = os.getenv("MINGW_CONFIGURATIONS", "")
    # 4.9@x86_64@seh@posix",4.9@x86_64@seh@win32"
    if not tmp:
        return []
    ret = []
    confs = tmp.split(",")
    for conf in confs:
        conf = conf.strip()
        ret.append(conf.split("@"))
    return ret


class PlatformInfo(object):
    """Easy mockable for testing"""
    def system(self):
        import platform
        return platform.system()


def split_colon_env(varname):
    return [a.strip() for a in list(filter(None, os.getenv(varname, "").split(",")))]


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
    default_gcc_versions = ["4.9", "5", "6", "7"]
    default_clang_versions = ["3.8", "3.9", "4.0"]
    default_visual_versions = ["10", "12", "14"]
    default_visual_runtimes = ["MT", "MD", "MTd", "MDd"]
    default_apple_clang_versions = ["7.3", "8.0", "8.1"]
    default_archs = ["x86", "x86_64"]
    default_build_types = ["Release", "Debug"]

    def __init__(self, args=None, username=None, channel=None, runner=None,
                 gcc_versions=None, visual_versions=None, visual_runtimes=None,
                 apple_clang_versions=None, archs=None,
                 use_docker=None, curpage=None, total_pages=None,
                 docker_image=None, reference=None, password=None, remote=None,
                 remotes=None,
                 upload=None, stable_branch_pattern=None,
                 vs10_x86_64_enabled=False,
                 mingw_configurations=None,
                 stable_channel=None,
                 platform_info=None,
                 upload_retry=None,
                 clang_versions=None,
                 login_username=None,
                 upload_only_when_stable=False,
                 build_types=None,
                 skip_check_credentials=False,
                 allow_gcc_minors=False,
                 exclude_vcvars_precommand=False,
                 docker_image_skip_update=False,
                 docker_entry_script=None,
                 docker_32_images=None):

        self.sudo_command = ""
        if "CONAN_DOCKER_USE_SUDO" in os.environ:
            if get_bool_from_env("CONAN_DOCKER_USE_SUDO"):
                self.sudo_command = "sudo"
        elif platform.system() == "Linux":
            self.sudo_command = "sudo"

        self.exclude_vcvars_precommand = exclude_vcvars_precommand or os.getenv("CONAN_EXCLUDE_VCVARS_PRECOMMAND", False)
        self.docker_image_skip_update = docker_image_skip_update or os.getenv("CONAN_DOCKER_IMAGE_SKIP_UPDATE", False)
        self.allow_gcc_minors = allow_gcc_minors or os.getenv("CONAN_ALLOW_GCC_MINORS", False)
        self._builds = []
        self._named_builds = {}
        self._platform_info = platform_info or PlatformInfo()
        self.runner = runner or os.system
        self.output_runner = ConanOutputRunner()
        self.args = args or " ".join(sys.argv[1:])
        self.username = username or os.getenv("CONAN_USERNAME", None)
        self.login_username = login_username or os.getenv("CONAN_LOGIN_USERNAME",
                                                          None) or self.username
        if not self.username:
            raise Exception("Instance ConanMultiPackage with 'username' "
                            "parameter or use CONAN_USERNAME env variable")

        # Upload related variables
        self.upload_retry = upload_retry or os.getenv("CONAN_UPLOAD_RETRY", 3)
        self.reference = reference or os.getenv("CONAN_REFERENCE", None)
        self.password = password or os.getenv("CONAN_PASSWORD", None)
        self.remote = remote or os.getenv("CONAN_REMOTE", None)

        # User is already logged
        self._logged_user_in_remote = defaultdict(lambda: False)

        if self.remote:
            raise Exception('''
'remote' argument is deprecated. Use:
        - 'upload' argument to specify the remote URL to upload your packages (or None to disable
        upload)
        - 'remotes' argument to specify additional remote URLs, for example, different user
        repositories.
''')

        self.remotes = remotes or os.getenv("CONAN_REMOTES", [])
        self.upload = upload if upload is not None else os.getenv("CONAN_UPLOAD", None)
        # The username portion of the remote URLs must be all lowercase to work
        if self.remotes:
            if isinstance(self.remotes,list):
                self.remotes = [remote.lower() for remote in self.remotes]
            else:
                self.remotes = self.remotes.lower()
        if self.upload:
            self.upload = self.upload.lower()

        self.stable_branch_pattern = stable_branch_pattern or \
                                     os.getenv("CONAN_STABLE_BRANCH_PATTERN", None)
        default_channel = channel or os.getenv("CONAN_CHANNEL", "testing")
        self.stable_channel = stable_channel or os.getenv("CONAN_STABLE_CHANNEL", "stable")
        self.channel = self._get_channel(default_channel, self.stable_channel)

        if self.reference:
            self.reference = ConanFileReference.loads("%s@%s/%s" % (self.reference,
                                                                    self.username, self.channel))
        self.upload_only_when_stable = upload_only_when_stable or \
                                       os.getenv("CONAN_UPLOAD_ONLY_WHEN_STABLE", False)
        self.skip_check_credentials = skip_check_credentials or \
                                      os.getenv("CONAN_SKIP_CHECK_CREDENTIALS", False)

        self.docker_entry_script = docker_entry_script or \
                                      os.getenv("CONAN_DOCKER_ENTRY_SCRIPT", None)

        if self.upload:
            if self.upload in ("0", "None", "False"):
                self.upload = None
            elif self.upload == "1":
                raise Exception("WARNING! 'upload' argument has changed. Use 'upload' argument or "
                                "CONAN_UPLOAD environment variable to specify a remote URL to "
                                "upload your packages. e.j: "
                                "upload='https://api.bintray.com/conan/myuser/myconanrepo'")

        os.environ["CONAN_CHANNEL"] = self.channel

        self.clang_versions = clang_versions or split_colon_env("CONAN_CLANG_VERSIONS")
        self.gcc_versions = gcc_versions or split_colon_env("CONAN_GCC_VERSIONS")

        # If there are some GCC versions declared then we don't default the clang
        # versions
        if not self.clang_versions and not self.gcc_versions:
            self.clang_versions = self.default_clang_versions

        # If there are some CLANG versions declared then we don't default the gcc
        # versions
        if not self.gcc_versions and self.clang_versions == self.default_clang_versions:
            self.gcc_versions = self.default_gcc_versions

        if self.gcc_versions and not self.allow_gcc_minors:
            for a_version in self.gcc_versions:
                if Version(a_version) >= Version("5") and "." in a_version:
                    raise Exception("""
******************* DEPRECATED GCC MINOR VERSIONS! ***************************************

- The use of gcc versions >= 5 and specifying the minor version (e.j "5.4") is deprecated.
- The ABI of gcc >= 5 (5, 6, and 7) is compatible between minor versions (e.j 5.3 is compatible with 5.4)
- Specify only the major in your script:
   - CONAN_GCC_VERSIONS="5,6,7" if you are using environment variables.
   - gcc_versions=["5", "6", "7"] if you are using the constructor parameter.

You can still keep using the same docker images, or use the new "lasote/conangcc5", "lasote/conangcc6", "lasote/conangcc7"

If you still want to keep the old behavior, set the environment var CONAN_ALLOW_GCC_MINORS or pass the
"allow_gcc_minors=True" parameter. But it is not recommended, if your packages are public most users
won't be able to use them.

******************************************************************************************

""")

        if visual_versions is not None:
            self.visual_versions = visual_versions
        else:
            self.visual_versions = split_colon_env("CONAN_VISUAL_VERSIONS")
            if not self.visual_versions and not mingw_configurations and not get_mingw_config_from_env():
                self.visual_versions = self.default_visual_versions
            elif mingw_configurations or get_mingw_config_from_env():
                self.visual_versions = []

        self.visual_runtimes = visual_runtimes or split_colon_env("CONAN_VISUAL_RUNTIMES") or \
                               self.default_visual_runtimes

        self.apple_clang_versions = apple_clang_versions or \
                                    split_colon_env("CONAN_APPLE_CLANG_VERSIONS") or \
                                    self.default_apple_clang_versions

        self.mingw_configurations = mingw_configurations or get_mingw_config_from_env()
        env_ref = os.getenv("CONAN_MINGW_INSTALLER_REFERENCE")
        self.mingw_installer_reference = ConanFileReference.loads(env_ref or
                                                                  "mingw_installer/1.0"
                                                                  "@conan/stable")

        self.archs = archs or split_colon_env("CONAN_ARCHS") or self.default_archs

        self.build_types = build_types or split_colon_env("CONAN_BUILD_TYPES") or \
                           self.default_build_types

        # If CONAN_DOCKER_IMAGE is speified, then use docker is True
        self.use_docker = use_docker or os.getenv("CONAN_USE_DOCKER", False) or \
                          (os.getenv("CONAN_DOCKER_IMAGE", None) is not None)

        if docker_32_images is not None:
            self.docker_32_images = docker_32_images
        else:
            self.docker_32_images = os.getenv("CONAN_DOCKER_32_IMAGES", False)

        self.curpage = curpage or os.getenv("CONAN_CURRENT_PAGE", 1)
        self.total_pages = total_pages or os.getenv("CONAN_TOTAL_PAGES", 1)
        self.docker_image = docker_image or os.getenv("CONAN_DOCKER_IMAGE", None)

        if self.password:
            self.password = self.password.replace('"', '\\"')

        self.conan_pip_package = os.getenv("CONAN_PIP_PACKAGE", "conan==%s" % client_version)
        self.vs10_x86_64_enabled = vs10_x86_64_enabled

        # Set the remotes
        if self.remotes:
            if not isinstance(self.remotes, list):
                self.remotes = [r.strip() for r in self.remotes.split(",") if r.strip()]
            for counter, remote in enumerate(reversed(self.remotes)):
                remote_name = "remote%s" % counter if remote != self.upload else "upload_repo"
                self.add_remote_safe(remote_name, remote, insert=True)
            self.runner("conan remote list")
        else:
            logger.info("Not additional remotes declared...")

        if self.upload and self.upload not in self.remotes:
            # If you specify the upload as a remote, put it first
            # this way we can cover all the possibilities
            self.add_remote_safe("upload_repo", self.upload, insert=False)

        _, client_cache, _ = Conan.factory()
        self.data_home = client_cache.store
        self.builds_in_current_page = []

    def get_remote_name(self, remote_url):
        # FIXME: Use conan api when prepared to return the list
        self.output_runner("conan remote list")
        for line in self.output_runner.output.splitlines():
            if remote_url in line:
                return line.split(":", 1)[0]
        return None

    def add_remote_safe(self, name, url, insert=False):
        # FIXME: Use conan api when prepared to call
        """Add a remove previoulsy removing if needed an already configured repository
        with the same URL"""
        existing_name = self.get_remote_name(url)
        if existing_name:
            self.runner("conan remote remove %s" % existing_name)

        if insert:
            if self.runner("conan remote add %s %s --insert" % (name, url)) != 0:
                logger.info("Remote add with insert failed... trying to add at the end")
            else:
                return 0
        self.runner("conan remote add %s %s" % (name, url))  # Retrocompatibility

    @property
    def items(self):
        return self._builds

    @items.setter
    def items(self, confs):
        self.builds = confs

    @property
    def builds(self):
        # Retrocompatibility iterating
        logger.warn("\n\n\n******** ITERATING THE CONAN_PACKAGE_TOOLS BUILDS WITH "
                    ".builds is deprecated use .items() instead (unpack 5 elements: "
                    "settings, options, env_vars, build_requires, reference  **********\n\n\n")
        return [elem[0:4] for elem in self._builds]

    @builds.setter
    def builds(self, confs):
        """For retrocompatibility directly assigning builds"""
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

        reference = reference or self.reference

        builds = []
        if self.use_docker:
            builds = get_linux_gcc_builds(self.gcc_versions, self.archs, shared_option_name,
                                          pure_c, self.build_types, reference)
            builds.extend(get_linux_clang_builds(self.clang_versions, self.archs,
                                                 shared_option_name, pure_c, self.build_types,
                                                 reference))
        else:
            if self._platform_info.system() == "Windows":
                if self.mingw_configurations:
                    builds = get_mingw_builds(self.mingw_configurations,
                                              self.mingw_installer_reference, self.archs,
                                              shared_option_name, self.build_types, reference)
                builds.extend(get_visual_builds(self.visual_versions, self.archs,
                                                self.visual_runtimes,
                                                shared_option_name, dll_with_static_runtime,
                                                self.vs10_x86_64_enabled, self.build_types,
                                                reference))
            elif self._platform_info.system() == "Linux":
                builds = get_linux_gcc_builds(self.gcc_versions, self.archs, shared_option_name,
                                              pure_c, self.build_types, reference)
                builds.extend(get_linux_clang_builds(self.clang_versions, self.archs,
                                                     shared_option_name, pure_c,
                                                     self.build_types, reference))
            elif self._platform_info.system() == "Darwin":
                builds = get_osx_apple_clang_builds(self.apple_clang_versions, self.archs,
                                                    shared_option_name, pure_c, self.build_types,
                                                    reference)
            elif self._platform_info.system() == "FreeBSD":
                builds = get_linux_clang_builds(self.clang_versions, self.archs,
                                                shared_option_name, pure_c, self.build_types,
                                                reference)

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

    def run(self, profile_name=None):
        if self.conan_pip_package:
            self.runner('%s pip install %s' % (self.sudo_command, self.conan_pip_package))
        if not self.skip_check_credentials and self._upload_enabled():
            self.login("upload_repo")
        self.run_builds(profile_name=profile_name)
        self.upload_packages()

    def run_builds(self, curpage=None, total_pages=None, profile_name=None):
        if len(self.named_builds) > 0 and len(self.items) > 0:
            raise Exception("Both bulk and named builds are set. Only one is allowed.")

        # self.runner('conan export %s/%s' % (self.username, self.channel))

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

        print("Page       : ", curpage)
        print("Builds list:")
        for p in self.builds_in_current_page:
            print(list(p._asdict().items()))

        pulled_docker_images = defaultdict(lambda: False)
        for build in self.builds_in_current_page:
            profile = self._get_profile(build, profile_name)
            if self.use_docker:
                use_docker_32 = (build.settings.get("arch", "") == "x86" and self.docker_32_images)
                build_runner = DockerTestPackageRunner(profile, self.username, self.channel,
                                                       build.reference,
                                                       self.mingw_installer_reference, self.runner,
                                                       self.args,
                                                       docker_image=self.docker_image,
                                                       conan_pip_package=self.conan_pip_package,
                                                       docker_image_skip_update=self.docker_image_skip_update,
                                                       docker_32_images=use_docker_32)

                build_runner.run(pull_image=not pulled_docker_images[build_runner.docker_image],
                                 docker_entry_script=self.docker_entry_script)
                pulled_docker_images[build_runner.docker_image] = True
            else:
                build_runner = TestPackageRunner(profile, self.username, self.channel,
                                                 build.reference,
                                                 self.mingw_installer_reference, self.runner,
                                                 self.args,
                                                 conan_pip_package=self.conan_pip_package,
                                                 exclude_vcvars_precommand=self.exclude_vcvars_precommand)
                build_runner.run()

    def login(self, remote_name, user=None, password=None, force=False):
        if force or not self._logged_user_in_remote[remote_name]:
            user_command = 'conan user %s -p="%s" -r=%s' % (user or self.login_username,
                                                            password or self.password,
                                                            remote_name)

            logger.info("******** VERIFYING YOUR CREDENTIALS **********\n")
            if self._platform_info.system() == "Linux" and self.use_docker:
                data_dir = os.path.expanduser(self.data_home)
                self.runner("%s chmod -R 777 %s" % (self.sudo_command, data_dir))

            ret = self.runner(user_command)
            if ret != 0:
                raise Exception("Error with user credentials for remote %s" % remote_name)

        self._logged_user_in_remote[remote_name] = True

    def upload_packages(self):
        if not self._upload_enabled():
            return

        self.login("upload_repo")

        all_refs = set([ref for _, _, _, _, ref in self.builds_in_current_page])

        if not all_refs:
            all_refs = [self.reference]

        if not all_refs:
            logger.error("******** NOT REFERENCES TO UPLOAD!! ********** \n")

        if self._platform_info.system() == "Linux" and self.use_docker:
            data_dir = os.path.expanduser(self.data_home)
            self.runner("%s chmod -R 777 %s" % (self.sudo_command, data_dir))

        for ref in all_refs:
            command = "conan upload %s --retry %s --all --force --confirm -r=upload_repo" % (
                    str(ref), self.upload_retry)

            logger.info("******** RUNNING UPLOAD COMMAND ********** \n%s" % command)
            ret = self.runner(command)
            if ret != 0:
                raise Exception("Error uploading")

    def _upload_enabled(self):
        if not self.upload:
            return False

        st_channel = self.stable_channel or "stable"
        if self.upload_only_when_stable and self.channel != st_channel:
            print("Skipping upload, not stable channel")
            return False

        if not os.getenv("CONAN_TEST_SUITE", False):
            if os.getenv("TRAVIS_PULL_REQUEST", "false") != "false" or \
               os.getenv("APPVEYOR_PULL_REQUEST_NUMBER") or \
               os.getenv("CIRCLE_PULL_REQUEST"):
                # PENDING! can't found info for gitlab/bamboo
                print("Skipping upload, this is a Pull Request")
                return False

        def raise_error(field):
            raise Exception("Upload not possible, '%s' is missing!" % field)

        if not self.password:
            raise_error("password")
        if not self.channel:
            raise_error("channel")
        if not self.username:
            raise_error("username")

        return True

    def _get_channel(self, default_channel, stable_channel):

        pattern = self.stable_branch_pattern or "master"
        prog = re.compile(pattern)

        travis = os.getenv("TRAVIS", False)
        travis_branch = os.getenv("TRAVIS_BRANCH", None)
        appveyor = os.getenv("APPVEYOR", False)
        appveyor_branch = os.getenv("APPVEYOR_REPO_BRANCH", None)
        bamboo = os.getenv("bamboo_buildNumber", False)
        bamboo_branch = os.getenv("bamboo_planRepository_branch", None)
        jenkins = os.getenv("JENKINS_URL", False)
        jenkins_branch = os.getenv("BRANCH_NAME", None)
        gitlab = os.getenv("GITLAB_CI", False)  # Mark that job is executed in GitLab CI environment
        gitlab_branch = os.getenv("CI_BUILD_REF_NAME", None)
        circleci = os.getenv("CIRCLECI", False)
        circleci_branch = os.getenv("CIRCLE_BRANCH", None)
        # The branch or tag name for which project is built

        channel = stable_channel if travis and prog.match(travis_branch) else None
        channel = stable_channel if appveyor and prog.match(appveyor_branch) and \
            not os.getenv("APPVEYOR_PULL_REQUEST_NUMBER") else channel
        channel = stable_channel if bamboo and prog.match(bamboo_branch) else channel
        channel = stable_channel if jenkins and jenkins_branch and prog.match(jenkins_branch) else channel
        channel = stable_channel if gitlab and gitlab_branch and prog.match(gitlab_branch) else channel
        channel = stable_channel if circleci and circleci_branch and prog.match(circleci_branch) else channel

        if channel:
            logger.warning("Redefined channel by CI branch matching with '%s', "
                           "setting CONAN_CHANNEL to '%s'" % (pattern, channel))
            self.username = os.getenv("CONAN_STABLE_USERNAME", self.username)
            self.password = os.getenv("CONAN_STABLE_PASSWORD", self.password)

        ret = channel or default_channel

        return ret

    @staticmethod
    def _get_profile(build_conf, profile_name):
        if profile_name:
            print("**************************************************")
            print("Using specified default base profile: %s" % profile_name)
            print("**************************************************")
        profile_name = profile_name or "default"
        tmp = """
include(%s)

[settings]
%s
[options]
%s
[env]
%s
[build_requires]
%s
"""
        settings = "\n".join(["%s=%s" % (k, v) for k, v in sorted(build_conf.settings.items())])
        options = "\n".join(["%s=%s" % (k, v) for k, v in build_conf.options.items()])
        env_vars = "\n".join(["%s=%s" % (k, v) for k, v in build_conf.env_vars.items()])
        br_lines = ""
        for pattern, build_requires in build_conf.build_requires.items():
            br_lines += "\n".join(["%s:%s" % (pattern, br) for br in build_requires])

        if os.getenv("CONAN_BUILD_REQUIRES"):
            brs = os.getenv("CONAN_BUILD_REQUIRES").split(",")
            brs = ['*:%s' % br.strip() if ":" not in br else br for br in brs]
            if br_lines:
                br_lines += "\n"
            br_lines += "\n".join(brs)

        profile_text = tmp % (profile_name, settings, options, env_vars, br_lines)
        return profile_text


if __name__ == "__main__":
    runner = ConanOutputRunner()
    runner("ls")
