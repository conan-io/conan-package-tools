# -*- coding: utf-8 -*-
import unittest

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

    new_conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    options = {"shared": [True, False], "foo": [True, False]}
    default_options = "shared=False", "foo=True"

    def build(self):
        self.output.warn("NEW")
"""

    def test_remove_updated_packages_env_var(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.old_conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_REMOVE_OUTDATED_PACKAGES": "1"}):
            mulitpackager = get_patched_multipackager(tc, build_policy="missing",
                                                      exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)
            self.assertIn("OLD", tc.out)
            self.assertIn("Removing outdated packages for 'lib/1.0@user/testing'", tc.out)

    def test_remove_updated_packages_params(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.old_conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user"}):
            mulitpackager = get_patched_multipackager(tc, build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      remove_outdated_packages=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)
            self.assertIn("OLD", tc.out)
            self.assertIn("Removing outdated packages for 'lib/1.0@user/testing'", tc.out)
