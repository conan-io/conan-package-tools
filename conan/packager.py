import os
import json
import pipes
import collections


class ConanMultiPackager(object):

    def __init__(self, args, username, channel, runner=None):
        self._builds = []
        self.args = args
        self.username = username
        self.channel = channel
        self.runner = runner or os.system

    def add(self, settings=None, options=None):
        settings = settings or {}
        options = options or {}
        self._builds.append([settings, options])

    def pack(self, curpage=1, total_pages=1):
        '''Excutes the package generation in current machine'''
        curpage = int(curpage)
        total_pages = int(total_pages)
        self.runner('conan export %s/%s' % (self.username, self.channel))
        for index, build in enumerate(self._builds):
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

    def upload_packages(self, reference, password):
        self.runner("conan user %s -p %s" % (self.username, password))
        ret = self.runner("conan upload %s/%s/%s --all --force" % (reference, self.username, self.channel))
        if ret != 0:
            raise Exception("Error uploading")

    def serialize(self):
        doc = {"args": self.args,
               "username": self.username,
               "channel": self.channel,
               "builds": self._builds}
        return json.dumps(doc)

    @staticmethod
    def deserialize(data):
        the_json = json.loads(data)
        ret = ConanMultiPackager(None, None, None)
        ret.args = the_json["args"]
        ret.username = the_json["username"]
        ret.channel = the_json["channel"]
        ret._builds = the_json["builds"]
        return ret

    def _execute_build(self, build):
        settings, options = build
        if settings.get("compiler", None) == "Visual Studio" and "compiler_version" in settings:
            self._execute_visual_studio_build(build)
        else:
            self._execute_test(None, settings, options)

    def _execute_visual_studio_build(self, settings, options):
        '''Sets the VisualStudio environment with vcvarsall for the specified version'''
        vcvars = 'call "%vs' + str(settings["compiler_version"]) + '0comntools%../../VC/vcvarsall.bat"'
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
