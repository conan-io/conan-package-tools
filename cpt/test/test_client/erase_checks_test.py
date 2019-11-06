# -*- coding: utf-8 -*-
import unittest
from parameterized import parameterized

from conans.client.tools import environment_append
from conans.test.utils.tools import TestClient, TestServer

from cpt.test.test_client.tools import get_patched_multipackager


class EraseTest(unittest.TestCase):

    old_conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def build(self):
        self.output.warn("OLD")
"""

    @parameterized.expand([
       ("1", "assertIn"),
       ("0", "assertNotIn")
    ])
    def test_remove_updated_packages_env_var(self, remove_packages, assert_func):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.old_conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_REMOVE_OUTDATED_PACKAGES": remove_packages}):
            mulitpackager = get_patched_multipackager(tc, build_policy="missing",
                                                      exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)
            self.assertIn("OLD", tc.out)
            getattr(self, assert_func)("Removing outdated packages for 'lib/1.0@user/mychannel'",
                                       tc.out)

    @parameterized.expand([
       (True, "assertIn"),
       (False, "assertNotIn")
    ])
    def test_remove_updated_packages_params(self, remove_packages, assert_func):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.old_conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user"}):
            mulitpackager = get_patched_multipackager(tc, build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      remove_outdated_packages=remove_packages)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)
            self.assertIn("OLD", tc.out)
            getattr(self, assert_func)("Removing outdated packages for 'lib/1.0@user/mychannel'",
                                       tc.out)
