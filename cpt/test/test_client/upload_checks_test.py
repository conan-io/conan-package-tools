import unittest

from conans.client.tools import environment_append
from conans.test.utils.tools import TestClient, TestServer

from cpt.test.test_client.tools import get_patched_multipackager


class UploadTest(unittest.TestCase):

    conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def build(self):
        self.output.warn("HALLO")
"""

    def test_dont_upload_non_built_packages(self):

        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)

            # With the same cache and server try to rebuild them with policy missing
            mulitpackager = get_patched_multipackager(tc, build_policy="missing",
                                                      exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertIn("Skipping upload for 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", tc.out)
            self.assertIn("Skipping upload for 2a623e3082a38f90cd2c3d12081161412de331b0", tc.out)
            self.assertNotIn("HALLO", tc.out)

            # Without any build policy they get built
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertNotIn("Skipping upload for 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", tc.out)
            self.assertNotIn("Skipping upload for 2a623e3082a38f90cd2c3d12081161412de331b0", tc.out)
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)
            self.assertIn("HALLO", tc.out)
