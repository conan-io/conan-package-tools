import os
import unittest

from conans.util.files import mkdir_tmp
from conans import __version__ as client_version

from conans import tools
from conans.client.conan_api import ConanAPIV1
from cpt.test.utils.tools import TestBufferConanOutput

CONAN_UPLOAD_URL = os.getenv("CONAN_UPLOAD_URL",
                             "https://conan.jfrog.io/conan/api/conan/conan-testsuite")
CONAN_UPLOAD_PASSWORD = os.getenv("CONAN_UPLOAD_PASSWORD", "")
CONAN_LOGIN_UPLOAD = os.getenv("CONAN_LOGIN_UPLOAD", "")


class BaseTest(unittest.TestCase):

    def setUp(self):
        self.old_folder = os.getcwd()
        self.tmp_folder = mkdir_tmp()
        os.chmod(self.tmp_folder, 0o777)
        self.conan_home = self.tmp_folder
        os.chdir(self.tmp_folder)
        # user_home = "c:/tmp/home"  # Cache
        self.old_env = dict(os.environ)
        os.environ.update({"CONAN_USER_HOME": self.conan_home, "CONAN_PIP_PACKAGE": "0"})
        self.output = TestBufferConanOutput()
        self.api, _, _ = ConanAPIV1.factory()
        self.api.create_app()
        self.client_cache = self.api.app.cache

    def tearDown(self):
        os.chdir(self.old_folder)
        os.environ.clear()
        os.environ.update(self.old_env)

    def save_conanfile(self, conanfile):
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)

    def create_project(self):
        with tools.chdir(self.tmp_folder):
            if tools.Version(client_version) >= "1.32.0":
                self.api.new("hello/0.1.0", pure_c=True, exports_sources=True)
            else:
                self.api.new("hello/0.1.0")

    @property
    def root_project_folder(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        for i in range(10):
            if "setup.py" in os.listdir(dir_path):
                return dir_path
            else:
                dir_path = os.path.abspath(os.path.join(dir_path, os.pardir))
        raise Exception("Cannot find root project folder")
