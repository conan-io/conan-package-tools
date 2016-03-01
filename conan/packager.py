import os
import json
import pipes
import collections
import platform
import copy


class ConanMultiPackager(object):

    def __init__(self, args, username, channel, runner=None):
        self.builds = []
        self.args = args
        self.username = username
        self.channel = channel
        self.runner = runner or os.system

    def add_common_builds(self, shared_option_name=None, visual_versions=None):

        visual_versions = visual_versions or [10, 12, 14]
        if platform.system() == "Windows":
            for visual_version in visual_versions:
                for arch in ["x86", "x86_64"]:
                    if arch == "x86_64" and visual_version == 10:  # Not available even in Appveyor
                        continue
                    self.add_visual_builds(visual_version, arch, shared_option_name)
        else:
            self.add_other_builds(shared_option_name)

    def add_visual_builds(self, visual_version, arch, shared_option_name):

        base_set = {"compiler": "Visual Studio",
                    "compiler.version": visual_version,
                    "arch": arch}
        sets = []

        if shared_option_name:
            sets.append([{"build_type": "Release", "compiler.runtime": "MT"}, {shared_option_name: False}])
            sets.append([{"build_type": "Debug", "compiler.runtime": "MTd"}, {shared_option_name: False}])
            sets.append([{"build_type": "Debug", "compiler.runtime": "MDd"}, {shared_option_name: False}])
            sets.append([{"build_type": "Release", "compiler.runtime": "MD"}, {shared_option_name: False}])
            sets.append([{"build_type": "Debug", "compiler.runtime": "MDd"}, {shared_option_name: True}])
            sets.append([{"build_type": "Release", "compiler.runtime": "MD"}, {shared_option_name: True}])
        else:
            sets.append([{"build_type": "Release", "compiler.runtime": "MT"}, {}])
            sets.append([{"build_type": "Debug", "compiler.runtime": "MTd"}, {}])
            sets.append([{"build_type": "Debug", "compiler.runtime": "MDd"}, {}])
            sets.append([{"build_type": "Release", "compiler.runtime": "MD"}, {}])

        for setting, options in sets:
            tmp = copy.copy(base_set)
            tmp.update(setting)
            self.add(tmp, options)

    def add_other_builds(self, shared_option_name):
        # Not specified compiler or compiler version, will use the auto detected
        for arch in ["x86", "x86_64"]:
            if shared_option_name:
                for shared in [True, False]:
                    for build_type in ["Debug", "Release"]:
                        self.add({"arch": arch, "build_type": build_type},
                                 {shared_option_name: shared})
            else:
                for build_type in ["Debug", "Release"]:
                    self.add({"arch": arch, "build_type": build_type}, {})

    def add(self, settings=None, options=None):
        # FIXME, could be boilerplate
        settings = settings or {}
        options = options or {}
        self.builds.append([settings, options])

    def pack(self, curpage=1, total_pages=1):
        '''Excutes the package generation in current machine'''
        curpage = int(curpage)
        total_pages = int(total_pages)
        self.runner('conan export %s/%s' % (self.username, self.channel))
        for index, build in enumerate(self.builds):
            if curpage is None or total_pages is None or (index % total_pages) + 1 == curpage:
                self._execute_build(build)

    def docker_pack(self, curpage=1, total_pages=1, gcc_versions=None):
        """Launch the package generator in docker containers, one per gcc version specified"""
        versions = gcc_versions or ["4.6", "4.8", "4.9", "5.2", "5.3"]
        for gcc_version in versions:
            # Do not change this "lasote" name is the dockerhub image, its a generic image
            # for build c/c++ with docker and gcc
            image_name = "lasote/conangcc%s" % gcc_version.replace(".", "")
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
            command = "sudo docker run --rm -v %s:/home/conan/project -v " \
                      "~/.conan/data:/home/conan/.conan/data -it %s %s /bin/sh -c \"" \
                      "cd project && sudo pip install conan_package_tools --upgrade && " \
                      "conan_json_packager\"" % (curdir, env_vars, image_name)
            ret = self.runner(command)
            if ret != 0:
                raise Exception("Error building: %s" % command)

    def upload_packages(self, reference, password, remote=None):
        """
        :param password: If it has double quotes, they must not be escaped, this function
        does escaping of double quotes automatically. It is suppposed that this password
        comes from travis or appveyor, in which you will not consider such issue.
        """
        password = password.replace('"', '\\"')
        self.runner('conan user %s -p="%s"' % (self.username, password))
        command = "conan upload %s/%s/%s --all --force" % (reference, self.username, self.channel)
        if remote:
            command += " -r %s" % remote
        ret = self.runner(command)
        if ret != 0:
            raise Exception("Error uploading")

    def serialize(self):
        doc = {"args": self.args,
               "username": self.username,
               "channel": self.channel,
               "builds": self.builds}
        return json.dumps(doc)

    @staticmethod
    def deserialize(data):
        the_json = json.loads(data)
        ret = ConanMultiPackager(None, None, None)
        ret.args = the_json["args"]
        ret.username = the_json["username"]
        ret.channel = the_json["channel"]
        ret.builds = the_json["builds"]
        return ret

    def _execute_build(self, build):
        settings, options = build
        if settings.get("compiler", None) == "Visual Studio" and "compiler.version" in settings:
            self._execute_visual_studio_build(settings, options)
        else:
            self._execute_test(None, settings, options)

    def _execute_visual_studio_build(self, settings, options):
        '''Sets the VisualStudio environment with vcvarsall for the specified version'''
        vcvars = 'call "%vs' + str(settings["compiler.version"]) + '0comntools%../../VC/vcvarsall.bat"'
        param = "x86" if settings.get("arch", None) == "x86" else "amd64"
        command = '%s %s' % (vcvars, param)
        self._execute_test(command, settings, options)

    def _execute_test(self, precommand, settings, options):
        settings = collections.OrderedDict(sorted(settings.items()))
        settings = " ".join(['-s %s="%s"' % (key, value) for key, value in settings.iteritems()])
        options = " ".join(['-o %s="%s"' % (key, value) for key, value in options.iteritems()])
        command = "conan test . %s %s %s" % (settings, options, self.args)
        if precommand:
            command = '%s && %s' % (precommand, command)

        print(">>>> %s" % command)
        retcode = self.runner(command)
        if retcode != 0:
            exit("Error while executing:\n\t %s" % command)
