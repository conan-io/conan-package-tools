import os
import unittest

from conans import tools
from conans.client.conan_api import ConanAPIV1
from conans.test.utils.tools import TestBufferConanOutput

PYPI_TESTING_REPO = os.getenv("PYPI_TESTING_REPO",
                              "https://conan.jfrog.io/conan/api/pypi/pypi_testing_conan")
PYPI_PASSWORD = os.getenv("PYPI_PASSWORD", None)


CONAN_UPLOAD_URL = os.getenv("CONAN_UPLOAD_URL",
                             "https://conan.jfrog.io/conan/api/conan/conan-testsuite")
CONAN_UPLOAD_PASSWORD = os.getenv("CONAN_UPLOAD_PASSWORD", "")
CONAN_LOGIN_UPLOAD = os.getenv("CONAN_LOGIN_UPLOAD", "")


pypi_template = """
[distutils]
index-servers =
   pypi_testing_conan

[pypi_testing_conan]
repository: %s
username: python
password: %s

""" % (PYPI_TESTING_REPO, PYPI_PASSWORD)


class BaseTest(unittest.TestCase):

    def setUp(self):
        self.old_folder = os.getcwd()
        self.tmp_folder = tools.mkdir_tmp()
        os.chmod(self.tmp_folder, 0o777)
        self.conan_home = self.tmp_folder
        os.chdir(self.tmp_folder)
        # user_home = "c:/tmp/home"  # Cache
        self.old_env = dict(os.environ)
        os.environ.update({"CONAN_USER_HOME": self.conan_home, "CONAN_PIP_PACKAGE": "0"})
        self.output = TestBufferConanOutput()
        self.api, self.client_cache, _ = ConanAPIV1.factory()
        print("Testing with Conan Folder=%s" % self.client_cache.conan_folder)

    def deploy_pip(self):
        if os.getenv("PYPI_PASSWORD", None):
            conf_path = os.path.expanduser("~/.pypirc")
            if not os.path.exists(conf_path):
                tools.save(conf_path, pypi_template)
            ret = os.system("cd %s && ls && python setup.py sdist upload -r pypi_testing_conan" % self.old_folder)
            if ret != 0:
                raise Exception("Failed publishing conan package tools")
            self.output.write("Deployed pip package")
        else:
            raise Exception("Skipped deploy of pip package!")

    def tearDown(self):
        os.chdir(self.old_folder)
        os.environ.clear()
        os.environ.update(self.old_env)

    def save_conanfile(self, conanfile):
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)
