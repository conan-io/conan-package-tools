import os
import re
import sys

from collections import defaultdict

from conans.client.runner import ConanRunner
from conans.model.ref import ConanFileReference

from conan.test_package_runner import TestPackageRunner, DockerTestPackageRunner
from conan.builds_generator import (get_linux_gcc_builds, get_linux_clang_builds, get_visual_builds,
                                    get_osx_apple_clang_builds, get_mingw_builds, BuildConf)
from conan.log import logger
from conans.model.profile import Profile


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
    and run conan test_package command in docker containers"""
    default_gcc_versions = ["4.6", "4.8", "4.9", "5.2", "5.3", "5.4", "6.2", "6.3"]
    default_clang_versions = ["3.8", "3.9", "4.0"]
    default_visual_versions = ["10", "12", "14"]
    default_visual_runtimes = ["MT", "MD", "MTd", "MDd"]
    default_apple_clang_versions = ["7.3", "8.0", "8.1"]
    default_archs = ["x86", "x86_64"]

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
                 login_username=None):

        self._builds = []
        self._named_builds = {}
        self._platform_info = platform_info or PlatformInfo()
        self.runner = runner or ConanOutputRunner()
        self.args = args or " ".join(sys.argv[1:])
        self.username = username or os.getenv("CONAN_USERNAME", None)
        self.login_username = login_username or os.getenv("CONAN_LOGIN_USERNAME", None) or self.username
        if not self.username:
            raise Exception("Instance ConanMultiPackage with 'username' "
                            "parameter or use CONAN_USERNAME env variable")

        # Upload related variables
        self.upload_retry = upload_retry or os.getenv("CONAN_UPLOAD_RETRY", 3)
        self.reference = reference or os.getenv("CONAN_REFERENCE", None)
        self.password = password or os.getenv("CONAN_PASSWORD", None)
        self.remote = remote or os.getenv("CONAN_REMOTE", None)

        if self.remote:
            raise Exception('''
'remote' argument is deprecated. Use:
        - 'upload' argument to specify the remote URL to upload your packages (or None to disable upload)
        - 'remotes' argument to specify additional remote URLs, for example, different user repositories.
''')

        self.remotes = remotes or os.getenv("CONAN_REMOTES", None)
        self.upload = upload or os.getenv("CONAN_UPLOAD", None)

        self.stable_branch_pattern = stable_branch_pattern or os.getenv("CONAN_STABLE_BRANCH_PATTERN", None)
        default_channel = channel or os.getenv("CONAN_CHANNEL", "testing")
        stable_channel = stable_channel or os.getenv("CONAN_STABLE_CHANNEL", "stable")
        self.channel = self._get_channel(default_channel, stable_channel)

        if self.upload:
            if self.upload in ("0", "None", "False"):
                self.upload = None
            elif self.upload == "1":
                raise Exception("WARNING! 'upload' argument has changed. Use 'upload' argument or CONAN_UPLOAD "
                                "environment variable to specify a remote URL to upload your packages. e.j: "
                                "upload='https://api.bintray.com/conan/myuser/myconanrepo'")
            elif not self.reference or not self.password or not self.channel or not self.username:
                raise Exception("Upload not possible, some parameter (reference, password or channel) is missing!")

        os.environ["CONAN_CHANNEL"] = self.channel

        self.clang_versions = clang_versions or list(filter(None, os.getenv("CONAN_CLANG_VERSIONS", "").split(",")))\

        # If there are some GCC versions declared in the environment then we don't default the clang versions
        if not self.clang_versions and not os.getenv("CONAN_GCC_VERSIONS", False):
            self.clang_versions = self.default_clang_versions

        self.gcc_versions = gcc_versions or list(filter(None, os.getenv("CONAN_GCC_VERSIONS", "").split(",")))

        # If there are some CLANG versions declared in the environment then we don't default the gcc versions
        if not self.gcc_versions and not os.getenv("CONAN_CLANG_VERSIONS", False):
            self.gcc_versions = self.default_gcc_versions

        if visual_versions is not None:
            self.visual_versions = visual_versions
        else:
            env_visual_versions = list(filter(None, os.getenv("CONAN_VISUAL_VERSIONS", "").split(",")))
            self.visual_versions = env_visual_versions or self.default_visual_versions
        self.visual_runtimes = visual_runtimes or \
            list(filter(None, os.getenv("CONAN_VISUAL_RUNTIMES", "").split(","))) or \
            self.default_visual_runtimes

        self.apple_clang_versions = apple_clang_versions or \
            list(filter(None, os.getenv("CONAN_APPLE_CLANG_VERSIONS", "").split(","))) or \
            self.default_apple_clang_versions

        self.mingw_configurations = mingw_configurations or get_mingw_config_from_env()
        self.mingw_installer_reference = ConanFileReference.loads(os.getenv("CONAN_MINGW_INSTALLER_REFERENCE") or
                                                                  "mingw_installer/0.1@lasote/testing")

        self.archs = archs or \
            list(filter(None, os.getenv("CONAN_ARCHS", "").split(","))) or \
            self.default_archs

        # If CONAN_DOCKER_IMAGE is speified, then use docker is True
        self.use_docker = use_docker or os.getenv("CONAN_USE_DOCKER", False) or (os.getenv("CONAN_DOCKER_IMAGE", None) is not None)

        self.curpage = curpage or os.getenv("CONAN_CURRENT_PAGE", 1)
        self.total_pages = total_pages or os.getenv("CONAN_TOTAL_PAGES", 1)
        self.docker_image = docker_image or os.getenv("CONAN_DOCKER_IMAGE", None)

        if self.password:
            self.password = self.password.replace('"', '\\"')

        self.conan_pip_package = os.getenv("CONAN_PIP_PACKAGE", None)
        self.vs10_x86_64_enabled = vs10_x86_64_enabled

        if self.upload:
            self.add_remote_safe("upload_repo", self.upload, insert=False)

        # Set the remotes
        if self.remotes:
            if not isinstance(self.remotes, list):
                remotes = [r.strip() for r in self.remotes.split(",") if r.strip()]

            for counter, remote in enumerate(reversed(remotes)):
                if remote == self.upload:  # Already added
                    continue
                remote_name = "remote%s" % counter
                self.add_remote_safe(remote_name, remote, insert=True)
            self.runner("conan remote list")
        else:
            logger.info("Not additional remotes declared...")

    def get_remote_name(self, remote_url):
        # FIXME: Use conan api when prepared to return the list
        self.runner("conan remote list")
        for line in self.runner.output.splitlines():
            if remote_url in line:
                return line.split(":", 1)[0]
        return None

    def add_remote_safe(self, name, url, insert=False):
        # FIXME: Use conan api when prepared to call
        """Add a remove previoulsy removing if needed an already configured repository with the same URL"""
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
    def builds(self):
        return self._builds

    @builds.setter
    def builds(self, confs):
        """For retrocompatibility directly assigning builds"""
        self._named_builds = {}
        self._builds = []
        for values in confs:
            if len(values) == 2:
                self._builds.append(BuildConf(values[0], values[1], {}, {}))
            elif len(values) != 4:
                raise Exception("Invalid build configuration, has to be a tuple of "
                                "(settings, options, env_vars, build_requires)")
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
                    self._named_builds.setdefault(key,[]).append(BuildConf(values[0], values[1], {}, {}))
                elif len(values) != 4:
                    raise Exception("Invalid build configuration, has to be a tuple of "
                                    "(settings, options, env_vars, build_requires)")
                else:
                    self._named_builds.setdefault(key,[]).append(BuildConf(*values))

    def add_common_builds(self, shared_option_name=None, pure_c=True, dll_with_static_runtime=False):
        builds = []
        if self._platform_info.system() == "Windows":
            if self.mingw_configurations:
                builds = get_mingw_builds(self.mingw_configurations, self.mingw_installer_reference, self.archs)
            builds.extend(get_visual_builds(self.visual_versions, self.archs, self.visual_runtimes,
                                            shared_option_name, dll_with_static_runtime, self.vs10_x86_64_enabled))
        elif self._platform_info.system() == "Linux":
            builds = get_linux_gcc_builds(self.gcc_versions, self.archs, shared_option_name, pure_c)
            builds.extend(get_linux_clang_builds(self.clang_versions, self.archs, shared_option_name, pure_c))
        elif self._platform_info.system() == "Darwin":
            builds = get_osx_apple_clang_builds(self.apple_clang_versions, self.archs, shared_option_name, pure_c)
        elif self._platform_info.system() == "FreeBSD":
            builds = get_linux_clang_builds(self.clang_versions, self.archs, shared_option_name, pure_c)

        self.builds.extend(builds)

    def add(self, settings=None, options=None, env_vars=None, build_requires=None):
        settings = settings or {}
        options = options or {}
        env_vars = env_vars or {}
        build_requires = build_requires or {}
        self.builds.append(BuildConf(settings, options, env_vars, build_requires))

    def run(self):
        self._pip_install()
        self.run_builds()
        self.upload_packages()

    def run_builds(self, curpage=None, total_pages=None):
        if len(self.named_builds) > 0 and len(self.builds) > 0:
            raise Exception("Both bulk and named builds are set. Only one is allowed.")

        self.runner('conan export %s/%s' % (self.username, self.channel))

        builds_in_current_page = []
        if len(self.builds) > 0:
            curpage = curpage or int(self.curpage)
            total_pages = total_pages or int(self.total_pages)
            for index, build in enumerate(self.builds):
                if curpage is None or total_pages is None or (index % total_pages) + 1 == curpage:
                    builds_in_current_page.append(build)
        elif len(self.named_builds) > 0:
            curpage = curpage or self.curpage
            if curpage not in self.named_builds:
                raise Exception("No builds set for page %s" % curpage)
            for build in self.named_builds[curpage]:
                builds_in_current_page.append(build)

        print("Page       : ", curpage)
        print("Builds list:")
        for p in builds_in_current_page: print(list(p._asdict().items()))

        pulled_docker_images = defaultdict(lambda: False)
        for build in builds_in_current_page:
            profile = _get_profile(build)
            if self.use_docker:
                build_runner = DockerTestPackageRunner(profile, self.username, self.channel,
                                                       self.mingw_installer_reference, self.runner, self.args,
                                                       docker_image=self.docker_image)

                build_runner.run(pull_image=not pulled_docker_images[build_runner.docker_image])
                pulled_docker_images[build_runner.docker_image] = True
            else:
                build_runner = TestPackageRunner(profile, self.username, self.channel,
                                                 self.mingw_installer_reference, self.runner, self.args)
                build_runner.run()

    def upload_packages(self):

        if not self.upload:
            return

        command = "conan upload %s@%s/%s --retry %s --all --force -r=upload_repo" % (self.reference, self.username,
                                                                                     self.channel, self.upload_retry)
        user_command = 'conan user %s -p="%s" -r=upload_repo' % (self.login_username, self.password)

        logger.info("******** RUNNING UPLOAD COMMAND ********** \n%s" % command)
        if self._platform_info.system() == "Linux" and self.use_docker:
            self.runner("sudo chmod -R 777 ~/.conan/data")
            # self.runner("ls -la ~/.conan")

        ret = self.runner(user_command)
        if ret != 0:
            raise Exception("Error with user credentials")

        ret = self.runner(command)
        if ret != 0:
            raise Exception("Error uploading")

    def _pip_install(self):

        if self.conan_pip_package:
            sudo = "sudo" if self._platform_info.system() != "Windows" else ""
            self.runner('%s pip install %s' % (sudo, self.conan_pip_package))

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
        gitlab_branch = os.getenv("CI_BUILD_REF_NAME", None)  # The branch or tag name for which project is built

        channel = stable_channel if travis and prog.match(travis_branch) else None
        channel = stable_channel if appveyor and prog.match(appveyor_branch) and \
            not os.getenv("APPVEYOR_PULL_REQUEST_NUMBER") else channel
        channel = stable_channel if bamboo and prog.match(bamboo_branch) else channel
        channel = stable_channel if jenkins and jenkins_branch and prog.match(jenkins_branch) else channel
        channel = stable_channel if gitlab and gitlab_branch and prog.match(gitlab_branch) else channel

        if channel:
            logger.warning("Redefined channel by CI branch matching with '%s', "
                           "setting CONAN_CHANNEL to '%s'" % (pattern, channel))
            self.username = os.getenv("CONAN_STABLE_USERNAME", self.username)
            self.password = os.getenv("CONAN_STABLE_PASSWORD", self.password)

        ret = channel or default_channel

        return ret


def _get_profile(build_conf):
    tmp = """
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

    profile_text = tmp % (settings, options, env_vars, br_lines)
    # FIXME: Remove when conan==0.24.0
    if hasattr(Profile, "loads"):
        return Profile.loads(profile_text)
    else:
        # Fixme, make public in conan?
        from conans.client.profile_loader import _load_profile
        return _load_profile(profile_text, None, None)[0]


if __name__ == "__main__":
    runner = ConanOutputRunner()
    runner("ls")

