import unittest
import os
import zipfile

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

    def test_upload_when_tag_is_false(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        zip_path = os.path.join(tc.current_folder, 'config.zip')
        zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        zipf.close()

        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_CONFIG_URL": zip_path, "CONAN_UPLOAD_ONLY_WHEN_TAG": "1",
                                 "TRAVIS": "1"}):

            mp = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mp.add_common_builds(shared_option_name=False)
            mp.run()

            self.assertNotIn("Redefined channel by branch tag", tc.out)
            self.assertNotIn("Uploading packages for 'lib/1.0@user/stable'", tc.out)
            self.assertNotIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9 to 'default'", tc.out)
            self.assertIn("Skipping upload, not tag branch", tc.out)

    def test_upload_when_tag_is_true(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        zip_path = os.path.join(tc.current_folder, 'config.zip')
        zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        zipf.close()

        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_CONFIG_URL": zip_path, "CONAN_UPLOAD_ONLY_WHEN_TAG": "1",
                                 "TRAVIS": "1", "TRAVIS_TAG": "0.1"}):

            mp = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mp.add_common_builds(shared_option_name=False)
            mp.run()

            self.assertNotIn("Skipping upload, not tag branch", tc.out)
            self.assertIn("Redefined channel by branch tag", tc.out)
            self.assertIn("Uploading packages for 'lib/1.0@user/stable'", tc.out)
            self.assertIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9 to 'default'", tc.out)
