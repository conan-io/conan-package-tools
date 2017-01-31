import os
import requests
import tempfile
from contextlib import contextmanager
from StringIO import StringIO
from subprocess import Popen, PIPE, STDOUT
from requests.auth import HTTPBasicAuth
from collections import defaultdict


BUILD_NAME = "prueba"
BUILD_NUMBER = 5


@contextmanager
def environment_append(env_vars):
    old_env = dict(os.environ)
    os.environ.update(env_vars)
    yield
    os.environ.clear()
    os.environ.update(old_env)


class RunnerOutput(object):

    def run(self, command, cwd=None, capture=False):

        if not capture:
            return os.system(command)
        else:
            output = StringIO()
        proc = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT, cwd=cwd)
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            output.write(line)
        out, err = proc.communicate()
        output.write(out)
        if err:
            output.write(err)

        return output.getvalue()


class BuildInfo(object):

    def __init__(self):
        # FIXME: Take it from ENV jenkins?
        self.name = BUILD_NAME
        self.version = "1.0"
        self.number = BUILD_NUMBER
        self.started = "2016-03-20T11:01:38.445+0200"
        self.modules = []

    def serialize(self):
        return {"version": self.version,
                "name": self.name,
                "number": self.number,
                "started": self.started,
                "modules": [module.serialize() for module in self.modules]}


class BuildInfoModule(object):

    def __init__(self):
        # Conan package or recipe
        self.id = ""
        self.artifacts = []
        self.dependencies = []

    def serialize(self):
        return {"id": self.id,
                "artifacts": [ar.serialize() for ar in self.artifacts],
                "dependencies": [dep.serialize() for dep in self.dependencies]}


class BuildInfoModuleArtifact(object):

    def __init__(self):
        # Each file in package
        self.type = ""
        self.sha1 = ""
        self.md5 = ""
        self.name = ""

    def serialize(self):
        return {"type": self.type,
                "sha1": self.sha1,
                "md5": self.md5,
                "name": self.name}


class BuildInfoModuleDependency(object):

    def __init__(self):
        # PROBLEM: In conan a package don't depend in a single file but another package
        # maybe we could link here the conaninfo?
        self.type = ""
        self.sha1 = ""
        self.md5 = ""
        self.id = ""


class ArtifactoryCIBuild(object):

    def __init__(self, art_url, user, password):
        # Prepend a CONAN_HOME to a tmp dir to keep it clean
        self.art_url = art_url
        self.user = user
        self.password = password
        self.info = BuildInfo()
        self.homedir = tempfile.mkdtemp(suffix='conan_ci')
        self.workdir = tempfile.mkdtemp(suffix='conan_ci_wd')
        self.chdir(self.workdir)
        self.runner = RunnerOutput()

    def create_remote(self, repo_name):
        # create the remote
        # conan/conan-local
        url = self.art_url + "/api/conan/%s" % repo_name
        self.run("conan remote add %s %s" % (repo_name, url))
        self.run("conan remote list")
        self.run("conan user %s -p %s -r %s" % (self.user, self.password, repo_name),
                 capture=True)  # Not show command passw in output

    def run(self, command, capture=False):
        with environment_append({"CONAN_USER_HOME": self.homedir, "CONAN_LOGGING_LEVEL": "50"}):
            ret = self.runner.run(command, capture=capture)
        return ret

    def chdir(self, chdir_to=None):
        os.chdir(chdir_to or self.workdir)

    def capture_published(self, upload_command, remote):
        # read the info and parse the conaninfo, get the deps and append to a dict
        output = self.run(upload_command + " -r %s --confirm" % remote, capture=True)
        modules_info = self._get_modules_info(output, remote)
        self.info.modules.extend(modules_info)

        print(self.info.serialize())

    def _get_modules_info(self, output, remote):
        """Returns a BuildInfoModule list for the recipe reference """
        ret = []
        uploaded_packages = capture_uploaded_packages(output)

        for recipe, packages in uploaded_packages.items():
            self.set_module_build_info(remote, recipe)
            for package in packages:
                module = BuildInfoModule()
                module.id = recipe + "#" + package
                # TODO: READ THE FOLDER LIST!
                tgz = self.get_build_info_artifact(remote, recipe, package, "conan_package.tgz")
                info = self.get_build_info_artifact(remote, recipe, package, "conaninfo.txt")
                module.artifacts.append(tgz)
                module.artifacts.append(info)
                ret.append(module)
        return ret

    def get_build_info_artifact(self, remote, recipe, package, file_name):
        info = self.read_artifact(remote, recipe, package, file_name)
        artifact = BuildInfoModuleArtifact()
        artifact.type = ""
        artifact.name = file_name
        artifact.sha1 = info["checksums"]["sha1"]
        artifact.md5 = info["checksums"]["md5"]
        return artifact

    def read_artifact(self, repo, reference, package_id, name):
        # /api/storage/libs-release-local/org/acme/lib/ver/
        url = self.art_url + "/api/storage/%s/%s/package/%s/%s" % (repo, reference.replace("@", '/'),
                                                                   package_id, name)
        ret = requests.get(url, json=self.info.serialize(),
                           auth=HTTPBasicAuth(self.user, self.password))
        if ret.status_code not in (200, 204):
            raise Exception(ret)
        return ret.json()

    def set_module_build_info(self, repo, reference):
        # /api/storage/libs-release-local/ch/qos/logback/logback-classic/0.9.9?properties=os=win,linux|qa=done&recursive=1
        props = "build.name=%s|build.number=%s" % (BUILD_NAME, BUILD_NUMBER)
        url = self.art_url + "/api/storage/%s/%s?properties=%s&recursive=1" % (repo, reference.replace("@", '/'), props)
        ret = requests.put(url, auth=HTTPBasicAuth(self.user, self.password))
        if ret.status_code not in (200, 204):
            raise Exception(ret)
        return

    def send_build_info(self):
        ret = requests.put(self.art_url + "/api/build", json=self.info.serialize(),
                           auth=HTTPBasicAuth(self.user, self.password))
        if ret.status_code not in (200, 204):
            raise Exception(ret)


def capture_uploaded_packages(output):
    """Conan feature recording activity in a json log? if ENV?"""
    print(output)
    uploading_recipe_text = "Uploaded conan recipe '"
    uploading_package_text = "Uploading package "

    ret = defaultdict(list)

    current_recipe = None
    for line in output.splitlines():
        if line.startswith(uploading_recipe_text):
            ref = line[len(uploading_recipe_text):]
            ref_last_post = ref.index(" ") - 1
            current_recipe = ref[0:ref_last_post]
        if line.startswith(uploading_package_text):
            sha = line[-40:]
            ret[current_recipe].append(sha)

    return ret


if __name__ == "__main__":
    art = ArtifactoryCIBuild("http://localhost:8081/artifactory", "admin", "password")
    art.create_remote("t1")
    art.run("git clone https://github.com/lasote/conan-zlib.git")
    art.chdir("./conan-zlib")
    art.run("conan test_package -r t1")
    art.capture_published('conan upload "zlib*" --all', 't1')
    art.send_build_info()
