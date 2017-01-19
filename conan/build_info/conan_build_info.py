import requests
import time
import json
import os
import hashlib
from collections import defaultdict
from requests.auth import HTTPBasicAuth
from time import strftime


def md5sum(file_path):
    return _generic_algorithm_sum(file_path, "md5")


def sha1sum(file_path):
    return _generic_algorithm_sum(file_path, "sha1")


def _generic_algorithm_sum(file_path, algorithm_name):

    with open(file_path, 'rb') as fh:
        m = hashlib.new(algorithm_name)
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()


class BuildInfo(object):

    def __init__(self, name=None, number=None, started=None):
        self.name = name
        self.number = number
        self.started = started or strftime("%Y-%m-%dT%H:%M:%S.000%z", time.gmtime())
        self.modules = []
        self.properties = {}

    def serialize(self):
        return {"name": self.name,
                "number": self.number,
                "started": self.started,
                "modules": [module.serialize() for module in self.modules],
                "properties": self.properties}


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


class BuildInfoManager(object):

    def build(self, trace_path, build_name, build_number, env_build_vars):
        bi = BuildInfo(name=build_name, number=build_number)
        modules = self._build_modules(trace_path)
        bi.modules.extend(modules)
        # Set the env vars
        for name, value in os.environ.items():
            if name not in env_build_vars:
                bi.properties["%s" % name] = value
        for name in env_build_vars:
            if name in os.environ:
                bi.properties["buildInfo.env.%s" % name] = os.environ[name]
        return bi

    def send(self, info, artifactory_url, repo_name, user, password):
        print("Sending build info...")
        self.send_build_info(info, artifactory_url, user, password)
        print("Linking published artifacts to the build...")
        self.set_repo_build_properties(info, artifactory_url, repo_name, user, password)
        print("Done!")

    def set_repo_build_properties(self, bi, artifactory_url, repo_name, user, password):
        for module in bi.modules:
            if ":" not in module.id:
                reference = module.id
                props = "build.name=%s|build.number=%s" % (bi.name, bi.number)
                tmp = "/api/storage/%s/%s?properties=%s&recursive=1" % (repo_name,
                                                                        reference.replace("@", '/'),
                                                                        props)
                url = artifactory_url + tmp
                ret = requests.put(url, auth=HTTPBasicAuth(user, password))
                if ret.status_code not in (200, 204):
                    raise Exception(ret)

    def send_build_info(self, info, artifactory_url, user, password):
        ret = requests.put(artifactory_url + "/api/build", json=info.serialize(),
                           auth=HTTPBasicAuth(user, password))
        if ret.status_code not in (200, 204):
            raise Exception(ret)

    def _build_modules(self, trace_path):
        modules = []
        modules_files = self._extract_from_conan_trace(trace_path)
        for module_id, files in modules_files.items():
            module = BuildInfoModule()
            module.id = module_id
            for the_file in files:
                artifact = self._get_build_info_artifact(the_file)
                module.artifacts.append(artifact)
            modules.append(module)
        return modules

    def _get_build_info_artifact(self, file_path):
        artifact = BuildInfoModuleArtifact()
        # FIXME: Weak
        artifact.type = "TGZ" if "tgz" in file_path else "TXT"
        artifact.name = os.path.basename(file_path)
        artifact.sha1 = sha1sum(file_path)
        artifact.md5 = md5sum(file_path)
        return artifact

    def _extract_from_conan_trace(self, path):
        modules = defaultdict(list)  # dict of {conan_ref: [abs_path1, abs_path2]}

        with open(path, "r") as traces:
            for line in traces.readlines():
                doc = json.loads(line)
                if doc["_action"] in ("UPLOADED_RECIPE", "UPLOADED_PACKAGE"):
                    for a_file in doc["files"].values():
                        modules[doc["_id"]].append(a_file)
        return modules



if __name__ == "__main__":
    run()
