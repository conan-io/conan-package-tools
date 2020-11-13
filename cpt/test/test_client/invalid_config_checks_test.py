import unittest

from conans.client.tools import environment_append
from cpt.test.utils.tools import TestClient, TestServer

from cpt.test.test_client.tools import get_patched_multipackager


class InvalidConfigTest(unittest.TestCase):

    conanfile = """from conans import ConanFile
from conans.errors import ConanInvalidConfiguration
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    settings = "arch"

    def configure(self):
        if self.settings.arch == "x86":
            raise ConanInvalidConfiguration("This library doesn't support x86")
"""

    def test_invalid_configuration_skipped_but_warned(self):

        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add({"arch": "x86_64"}, {})
            mulitpackager.add({"arch": "x86"}, {})
            mulitpackager.run()
            self.assertIn("Uploading package 1/1", tc.out)
            self.assertIn("Invalid configuration: This library doesn't support x86", tc.out)
