import os
import json
import pipes
import collections
import platform
import copy
import re
from conan.log import logger
import sys
from six import iteritems


class ConanMultiPackager(object):
    """ Help to generate common builds (setting's combinations), adjust the environment,
    and run conan test command in docker containers"""
    default_gcc_versions = ["4.6", "4.8", "4.9", "5.2", "5.3"]
    default_visual_versions = ["10", "12", "14"]
    default_visual_runtimes = ["MT", "MD", "MTd", "MDd"]
    default_apple_clang_versions = ["5.0", "5.1", "6.0", "6.1", "7.0", "7.3"]
    default_archs = ["x86", "x86_64"]

    def __init__(self, args=None, username=None, channel=None, runner=None,
                 gcc_versions=None, visual_versions=None, visual_runtimes=None,
                 apple_clang_versions=None, archs=None,
                 use_docker=None, curpage=None, total_pages=None,
                 docker_image=None, reference=None, password=None, remote=None,
                 upload=None, stable_branch_pattern=None,
                 vs10_x86_64_enabled=False):
        self.builds = []
        self.runner = runner or os.system
        self.logger = logger
        self.args = args or " ".join(sys.argv[1:])
        self.username = username or os.getenv("CONAN_USERNAME", None)
        if not self.username:
            raise Exception("Instance ConanMultiPackage with 'username' "
                            "parameter or use CONAN_USERNAME env variable")

        # Upload related variables
        self.reference = reference or os.getenv("CONAN_REFERENCE", None)
        self.password = password or os.getenv("CONAN_PASSWORD", None)
        self.remote = remote or os.getenv("CONAN_REMOTE", None)
        self.upload = upload or os.getenv("CONAN_UPLOAD", None)
        self.stable_branch_pattern = stable_branch_pattern or os.getenv("CONAN_STABLE_BRANCH_PATTERN", None)
        self.channel = self._get_channel(channel)
        os.environ["CONAN_CHANNEL"] = self.channel

        self.gcc_versions = gcc_versions or \
            list(filter(None, os.getenv("CONAN_GCC_VERSIONS", "").split(","))) or \
            self.default_gcc_versions
        self.visual_versions = visual_versions or \
            list(filter(None, os.getenv("CONAN_VISUAL_VERSIONS", "").split(","))) or \
            self.default_visual_versions
        self.visual_runtimes = visual_runtimes or \
            list(filter(None, os.getenv("CONAN_VISUAL_RUNTIMES", "").split(","))) or \
            self.default_visual_runtimes

        self.apple_clang_versions = apple_clang_versions or \
            list(filter(None, os.getenv("CONAN_APPLE_CLANG_VERSIONS", "").split(","))) or \
            self.default_apple_clang_versions

        self.archs = archs or \
            list(filter(None, os.getenv("CONAN_ARCHS", "").split(","))) or \
            self.default_archs

        self.use_docker = use_docker or os.getenv("CONAN_USE_DOCKER", False)
        self.curpage = curpage or os.getenv("CONAN_CURRENT_PAGE", 1)
        self.total_pages = total_pages or os.getenv("CONAN_TOTAL_PAGES", 1)
        self.docker_image = docker_image or os.getenv("CONAN_DOCKER_IMAGE", None)

        if self.password:
            self.password = self.password.replace('"', '\\"')

        self.conan_pip_package = os.getenv("CONAN_PIP_PACKAGE", None)
        self.vs10_x86_64_enabled = vs10_x86_64_enabled

    def _execute_test(self, precommand, settings, options):
        settings = collections.OrderedDict(sorted(settings.items()))

        if settings.get("compiler") != "Visual Studio":  # Pending until issue #186 is done
            if settings.get("compiler", None) and settings.get("compiler.version", None):
                conan_compiler, conan_compiler_version = self.conan_compiler_info()
                if conan_compiler != settings.get("compiler") or \
                   conan_compiler_version != settings.get("compiler.version"):
                    self.logger.debug("- Skipped build, compiler mismatch: %s" % str(dict(settings)))
                    return  # Skip this build, it's not for this machine

        settings = " ".join(['-s %s="%s"' % (key, value) for key, value in iteritems(settings)])
        options = " ".join(['-o %s="%s"' % (key, value) for key, value in iteritems(options)])
        command = "conan test . %s %s %s" % (settings, options, self.args)
        if precommand:
            command = '%s && %s' % (precommand, command)

        self.logger.info("******** RUNNING BUILD ********** \n%s" % command)
        retcode = self.runner(command)
        if retcode != 0:
            exit("Error while executing:\n\t %s" % command)

    def add_common_builds(self, shared_option_name=None, pure_c=True, visual_versions=None):

        if visual_versions:
            self.logger.warn("Parameter 'visual_versions' for 'add_common_builds' method are"
                             " deprecated and will be removed soon. Please use the specified "
                             "in the project docss.")
            self.visual_versions = visual_versions
        if platform.system() == "Windows":
            for visual_version in self.visual_versions:
                visual_version = str(visual_version)
                for arch in self.archs:
                    if not self.vs10_x86_64_enabled and arch == "x86_64" and visual_version == "10":
                        continue
                    self._add_visual_builds(visual_version, arch, shared_option_name)
        elif platform.system() == "Linux":
            self._add_linux_gcc_builds(shared_option_name, pure_c)
        elif platform.system() == "Darwin":
            self._add_osx_apple_clang_builds(shared_option_name, pure_c)

    def _add_visual_builds(self, visual_version, arch, shared_option_name):

        base_set = {"compiler": "Visual Studio",
                    "compiler.version": visual_version,
                    "arch": arch}
        sets = []

        if shared_option_name:
            if "MT" in self.visual_runtimes:
                sets.append([{"build_type": "Release", "compiler.runtime": "MT"},
                             {shared_option_name: False}])
            if "MTd" in self.visual_runtimes:
                sets.append([{"build_type": "Debug", "compiler.runtime": "MTd"},
                             {shared_option_name: False}])
            if "MD" in self.visual_runtimes:
                sets.append([{"build_type": "Release", "compiler.runtime": "MD"},
                             {shared_option_name: False}])
                sets.append([{"build_type": "Release", "compiler.runtime": "MD"},
                             {shared_option_name: True}])
            if "MDd" in self.visual_runtimes:
                sets.append([{"build_type": "Debug", "compiler.runtime": "MDd"},
                             {shared_option_name: False}])
                sets.append([{"build_type": "Debug", "compiler.runtime": "MDd"},
                             {shared_option_name: True}])

        else:
            if "MT" in self.visual_runtimes:
                sets.append([{"build_type": "Release", "compiler.runtime": "MT"}, {}])
            if "MTd" in self.visual_runtimes:
                sets.append([{"build_type": "Debug", "compiler.runtime": "MTd"}, {}])
            if "MDd" in self.visual_runtimes:
                sets.append([{"build_type": "Debug", "compiler.runtime": "MDd"}, {}])
            if "MD" in self.visual_runtimes:
                sets.append([{"build_type": "Release", "compiler.runtime": "MD"}, {}])

        for setting, options in sets:
            tmp = copy.copy(base_set)
            tmp.update(setting)
            self.add(tmp, options)

    def _add_osx_apple_clang_builds(self, shared_option_name, pure_c):
        # Not specified compiler or compiler version, will use the auto detected
        for compiler_version in self.apple_clang_versions:
            for arch in self.archs:
                if shared_option_name:
                    for shared in [True, False]:
                        for build_type in ["Debug", "Release"]:
                            if not pure_c:
                                self.add({"arch": arch,
                                          "build_type": build_type,
                                          "compiler": "apple-clang",
                                          "compiler.version": compiler_version,
                                          "compiler.libcxx": "libc++"},
                                         {shared_option_name: shared})
                            else:
                                self.add({"arch": arch,
                                          "build_type": build_type,
                                          "compiler": "apple-clang",
                                          "compiler.version": compiler_version},
                                         {shared_option_name: shared})
                else:
                    for build_type in ["Debug", "Release"]:
                        if not pure_c:
                            self.add({"arch": arch,
                                      "build_type": build_type,
                                      "compiler": "apple-clang",
                                      "compiler.version": compiler_version,
                                      "compiler.libcxx": "libc++"}, {})
                        else:
                            self.add({"arch": arch,
                                      "build_type": build_type,
                                      "compiler": "apple-clang",
                                      "compiler.version": compiler_version}, {})

    def _add_linux_gcc_builds(self, shared_option_name, pure_c):
        # Not specified compiler or compiler version, will use the auto detected
        for gcc_version in self.gcc_versions:
            for arch in self.archs:
                if shared_option_name:
                    for shared in [True, False]:
                        for build_type in ["Debug", "Release"]:
                            if not pure_c:
                                self.add({"arch": arch,
                                          "build_type": build_type,
                                          "compiler": "gcc",
                                          "compiler.version": gcc_version,
                                          "compiler.libcxx": "libstdc++"},
                                         {shared_option_name: shared})
                                if float(gcc_version) > 5:
                                    self.add({"arch": arch,
                                              "build_type": build_type,
                                              "compiler": "gcc",
                                              "compiler.version": gcc_version,
                                              "compiler.libcxx": "libstdc++11"},
                                             {shared_option_name: shared})
                            else:
                                self.add({"arch": arch,
                                          "build_type": build_type,
                                          "compiler": "gcc",
                                          "compiler.version": gcc_version},
                                         {shared_option_name: shared})
                else:
                    for build_type in ["Debug", "Release"]:
                        if not pure_c:
                            self.add({"arch": arch,
                                      "build_type": build_type,
                                      "compiler": "gcc",
                                      "compiler.version": gcc_version,
                                      "compiler.libcxx": "libstdc++"}, {})
                            if float(gcc_version) > 5:
                                self.add({"arch": arch,
                                          "build_type": build_type,
                                          "compiler": "gcc",
                                          "compiler.version": gcc_version,
                                          "compiler.libcxx": "libstdc++11"}, {})
                        else:
                            self.add({"arch": arch,
                                      "build_type": build_type,
                                      "compiler": "gcc",
                                      "compiler.version": gcc_version}, {})

    def add(self, settings=None, options=None):
        settings = settings or {}
        options = options or {}
        self.builds.append([settings, options])

    def run(self):
        self._pack()
        self._upload_packages()

    def pack(self, curpage=1, total_pages=1):
        self.curpage = int(curpage)
        self.total_pages = total_pages
        self._pack()

    def _pack(self):
        '''Excutes the package generation in currenConanMultiPackagert machine'''
        if self.conan_pip_package:
            sudo = "sudo" if platform.system() != "Windows" else ""
            self.runner('%s pip install %s' % (sudo, self.conan_pip_package))
        if not self.use_docker:
            curpage = int(self.curpage)
            total_pages = int(self.total_pages)
            self.runner('conan export %s/%s' % (self.username, self.channel))

            # Auto remove conan.conf if exist for perform a fresh detection
            self.runner("conan info")  # Ensure conan.conf is created

            for index, build in enumerate(self.builds):
                if curpage is None or total_pages is None or (index % total_pages) + 1 == curpage:
                    self._execute_build(build)
        else:
            self._docker_pack(self.curpage, self.total_pages, self.docker_image)

    def docker_pack(self, curpage=1, total_pages=1, gcc_versions=None):
        self.logger.warn("Docker pack is deprecated and will be removed soon.\n Please"
                         " instance ConanMultiPackager with 'use_docker=True' parameter and call run().")

        self.gcc_versions = gcc_versions or self.gcc_versions
        self.use_docker = True
        self.pack(curpage, total_pages)

    def _docker_pack(self, curpage=1, total_pages=1, docker_image=None):
        """Launch the package generator in docker containers, one per gcc version specified"""
        for gcc_version in self.gcc_versions:
            # Do not change this "lasote" name is the dockerhub image, its a generic image
            # for build c/c++ with docker and gcc
            image_name = docker_image or "lasote/conangcc%s" % gcc_version.replace(".", "")
            # FIXME: adjust for invoke from windows or mac (AND REMOVE SUDO)
            if not os.path.exists(os.path.expanduser("~/.conan/data")):  # Maybe for travis
                self.runner("mkdir ~/.conan/data && chmod -R 777 ~/.conan/data")
            self.runner("sudo docker pull %s" % image_name)
            curdir = os.path.abspath(os.path.curdir)
            serial = pipes.quote(self.serialize())
            env_vars = "-e CONAN_CURRENT_PAGE=%s -e CONAN_TOTAL_PAGES=%s " \
                       "-e CONAN_BUILDER_ENCODED=%s -e CONAN_USERNAME=%s " \
                       "-e CONAN_CHANNEL=%s" % (curpage, total_pages, serial,
                                                self.username, self.channel)
            if self.conan_pip_package:
                specific_conan_package = "&& sudo pip install %s" % self.conan_pip_package
            else:
                specific_conan_package = "&& sudo pip install conan --upgrade"

            command = "sudo docker run --rm -v %s:/home/conan/project -v " \
                      "~/.conan/data:/home/conan/.conan/data -it %s %s /bin/sh -c \"" \
                      "cd project && sudo pip install conan_package_tools --upgrade %s && " \
                      "conan_json_packager\"" % (curdir, env_vars, image_name, specific_conan_package)
            ret = self.runner(command)
            if ret != 0:
                raise Exception("Error building: %s" % command)

    def upload_packages(self, reference, password, remote=None):
        self.logger.warn("Method upload_packages is deprecated and will be removed soon.\n Please"
                         " instance ConanMultiPackager with 'reference', 'password', 'remote' and"
                         " 'upload' parameters"
                         " or use the environment variables and call run(). Read the project docs "
                         "for more information")
        self.reference = reference
        self.password = password.replace('"', '\\"')
        self.remote = remote
        self._upload_packages()

    def _upload_packages(self):
        """
        :param password: If it has double quotes, they must not be escaped, this function
        does escaping of double quotes automatically. It is supposed that this password
        comes from travis or appveyor, in which you will not consider such issue.
        """
        if not self.upload:
            return;
        if not self.reference or not self.password or not self.channel or not self.username:
            self.logger.info("Skipped upload, some parameter (reference, password or channel)"
                             " is missing!")
            return
        command = "conan upload %s@%s/%s --all --force" % (self.reference,
                                                           self.username,
                                                           self.channel)
        user_command = 'conan user %s -p="%s"' % (self.username, self.password)

        self.logger.info("******** RUNNING UPLOAD COMMAND ********** \n%s" % command)

        if self.remote:
            command += " -r %s" % self.remote
            user_command += " -r %s" % self.remote

        ret = self.runner(user_command)
        if ret != 0:
            raise Exception("Error with user credentials")

        ret = self.runner(command)
        if ret != 0:
            raise Exception("Error uploading")

    def serialize(self):
        doc = {"args": self.args,
               "username": self.username,
               "channel": self.channel,
               "builds": self.builds,
               "docker_image": self.docker_image,
               "conan_pip_package": self.conan_pip_package}
        return json.dumps(doc)

    @staticmethod
    def deserialize(data, username=None):
        the_json = json.loads(data)
        ret = ConanMultiPackager(username=username)
        ret.args = the_json["args"]
        ret.username = the_json["username"]
        ret.channel = the_json["channel"]
        ret.builds = the_json["builds"]
        ret.docker_image = the_json["docker_image"]
        ret.conan_pip_package = the_json["conan_pip_package"]
        return ret

    def _execute_build(self, build):
        settings, options = build
        if settings.get("compiler", None) == "Visual Studio" and "compiler.version" in settings:
            self._execute_visual_studio_build(settings, options)
        else:
            self._execute_test(None, settings, options)

    def _execute_visual_studio_build(self, settings, options):
        '''Sets the VisualStudio environment with vcvarsall for the specified version'''
        compiler_version = settings["compiler.version"]
        vcvars = 'call "%vs' + str(compiler_version) + '0comntools%../../VC/vcvarsall.bat"'
        param = "x86" if settings.get("arch", None) == "x86" else "amd64"
        command = '%s %s' % (vcvars, param)
        self._execute_test(command, settings, options)

    def conan_compiler_info(self):
        """return the compiler and its version readed in conan.conf"""
        from six.moves import configparser
        parser = configparser.ConfigParser()
        parser.read(os.path.expanduser("~/.conan/conan.conf"))
        items = dict(parser.items("settings_defaults"))
        return items["compiler"], items["compiler.version"]

    def _get_channel(self, default_channel):

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

        channel = "stable" if travis and prog.match(travis_branch) else None
        channel = "stable" if appveyor and prog.match(appveyor_branch) and \
            not os.getenv("APPVEYOR_PULL_REQUEST_NUMBER") else channel
        channel = "stable" if bamboo and prog.match(bamboo_branch) else channel
        channel = "stable" if jenkins and prog.match(jenkins_branch) else channel

        ret = channel or default_channel or os.getenv("CONAN_CHANNEL", "testing")
        if ret != os.getenv("CONAN_CHANNEL", "testing"):
            self.logger.warning("Redefined channel by CI branch matching with '%s', "
                                "setting CONAN_CHANNEL to '%s'" % (pattern, ret))

        return ret


if __name__ == "__main__":
    mp = ConanMultiPackager()
    print(mp.conan_compiler_info())
