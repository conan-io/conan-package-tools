import os
import unittest

from conans import tools
from conans.client.conan_api import ConanAPIV1
from conans.test.utils.tools import TestBufferConanOutput


class BaseTest(unittest.TestCase):

    def setUp(self):
        self.old_folder = os.getcwd()
        self.tmp_folder = tools.mkdir_tmp()
        self.conan_home = self.tmp_folder
        os.chdir(self.tmp_folder)
        # user_home = "c:/tmp/home"  # Cache
        self.old_env = dict(os.environ)
        os.environ.update({"CONAN_USER_HOME": self.conan_home, "CONAN_PIP_PACKAGE": "0"})
        self.output = TestBufferConanOutput()
        self.api, _, _ = ConanAPIV1.factory()

    def tearDown(self):
        os.chdir(self.old_folder)
        os.environ.clear()
        os.environ.update(self.old_env)

    def save_conanfile(self, conanfile):
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)