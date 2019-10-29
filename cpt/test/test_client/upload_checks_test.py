import unittest
import os
import zipfile

from conans.client.tools import environment_append
from conans.test.utils.tools import TestClient, TestServer
from cpt.test.unit.utils import MockCIManager

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

    def setUp(self):
        self._ci_manager = MockCIManager()

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

    def test_upload_only_recipe_env_var(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        # Upload only the recipe
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_UPLOAD_ONLY_RECIPE": "TRUE", "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()

            self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", tc.out)
            self.assertIn("Uploading lib/1.0@user/mychannel to remote", tc.out)
            self.assertIn("Uploaded conan recipe 'lib/1.0@user/mychannel'", tc.out)
            self.assertNotIn("Uploading package 1/2", tc.out)
            self.assertNotIn("Uploading package 2/2", tc.out)

        # Re-use cache the upload the binary packages
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_UPLOAD_ONLY_RECIPE": "FALSE", "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()

            self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", tc.out)
            self.assertIn("Uploading lib/1.0@user/mychannel to remote", tc.out)
            self.assertIn("Recipe is up to date, upload skipped", tc.out)
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)

    def test_upload_only_recipe_params(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        # Upload only the recipe
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      upload_only_recipe=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()

            self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", tc.out)
            self.assertIn("Uploading lib/1.0@user/mychannel to remote", tc.out)
            self.assertIn("Uploaded conan recipe 'lib/1.0@user/mychannel'", tc.out)
            self.assertNotIn("Uploading package 1/2", tc.out)
            self.assertNotIn("Uploading package 2/2", tc.out)

        # Re-use cache the upload the binary packages
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                "CONAN_CHANNEL": "mychannel"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      upload_only_recipe=False,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()

            self.assertIn(" Uploading packages for 'lib/1.0@user/mychannel'", tc.out)
            self.assertIn("Uploading lib/1.0@user/mychannel to remote", tc.out)
            self.assertIn("Recipe is up to date, upload skipped", tc.out)
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)

    def test_upload_package_revisions(self):
        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_REVISIONS_ENABLED": "1"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {"shared": True})
            mulitpackager.add({}, {"shared": False})
            mulitpackager.run()
            self.assertNotIn("Skipping upload for 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", tc.out)
            self.assertNotIn("Skipping upload for 2a623e3082a38f90cd2c3d12081161412de331b0", tc.out)
            self.assertIn("Uploading package 1/2", tc.out)
            self.assertIn("Uploading package 2/2", tc.out)
            self.assertIn("HALLO", tc.out)


class UploadDependenciesTest(unittest.TestCase):

    conanfile_bar = """from conans import ConanFile
class Pkg(ConanFile):
    name = "bar"
    version = "0.1.0"

    def build(self):
        pass
    """

    conanfile_foo = """from conans import ConanFile
class Pkg(ConanFile):
    name = "foo"
    version = "1.0.0"
    options = {"shared": [True, False]}
    default_options = "shared=True"

    def build(self):
        pass
    """

    conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "foobar"
    version = "2.0"
    requires = "bar/0.1.0@foo/stable", "foo/1.0.0@bar/testing"

    def build(self):
        self.output.warn("BUILDING")
"""

    def setUp(self):
        self._ci_manager = MockCIManager()
        self._server = TestServer(users={"user": "password"},
                                  write_permissions=[("bar/0.1.0@foo/stable", "user"),
                                                     ("foo/1.0.0@bar/testing", "user")])
        self._client = TestClient(servers={"default": self._server},
                                 users={"default": [("user", "password")]})
        self._client.save({"conanfile_bar.py": self.conanfile_bar})
        self._client.run("export conanfile_bar.py foo/stable")
        self._client.save({"conanfile_foo.py": self.conanfile_foo})
        self._client.run("export conanfile_foo.py bar/testing")
        self._client.save({"conanfile.py": self.conanfile})

    def test_upload_all_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "all"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {})
            mulitpackager.run()

            self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploaded conan recipe 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploading package 1/1: f88b82969cca9c4bf43f9effe1157e641f38f16d", self._client.out)

            self.assertIn("Uploading packages for 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertIn("Uploaded conan recipe 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", self._client.out)

            self.assertIn("Uploading packages for 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertIn("Uploaded conan recipe 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertIn("Uploading package 1/1: 2a623e3082a38f90cd2c3d12081161412de331b0", self._client.out)

    def test_invalid_upload_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "all,bar/0.1.0@foo/stable"}):
            with self.assertRaises(Exception) as context:
                get_patched_multipackager(self._client, exclude_vcvars_precommand=True)
            self.assertIn("Upload dependencies only accepts or 'all' or package references. Do not mix both!", str(context.exception))


    def test_upload_specific_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "foo/1.0.0@bar/testing"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {})
            mulitpackager.run()

            self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploaded conan recipe 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploading package 1/1: f88b82969cca9c4bf43f9effe1157e641f38f16d", self._client.out)

            self.assertNotIn("Uploading packages for 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertNotIn("Uploaded conan recipe 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertNotIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", self._client.out)

            self.assertIn("Uploading packages for 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertIn("Uploaded conan recipe 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertIn("Uploading package 1/1: 2a623e3082a38f90cd2c3d12081161412de331b0", self._client.out)

    def test_upload_regex_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "foo/*"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)

            mulitpackager.add({}, {})
            mulitpackager.run()

            self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploaded conan recipe 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploading package 1/1: f88b82969cca9c4bf43f9effe1157e641f38f16d", self._client.out)

            self.assertNotIn("Uploading packages for 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertNotIn("Uploaded conan recipe 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertNotIn("Uploading package 1/1: 5ab84d6acfe1f23c4fae0ab88f26e3a396351ac9", self._client.out)

            self.assertNotIn("Uploading packages for 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertNotIn("Uploaded conan recipe 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertNotIn("Uploading package 1/1: 2a623e3082a38f90cd2c3d12081161412de331b0", self._client.out)
