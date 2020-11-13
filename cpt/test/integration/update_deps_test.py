import unittest

from conans.client.tools import environment_append
from cpt.test.utils.tools import TestClient, TestServer
from cpt.test.unit.utils import MockCIManager
from cpt.test.test_client.tools import get_patched_multipackager



class UpdateTest(unittest.TestCase):

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

    conanfile_foo_2 = """from conans import ConanFile
class Pkg(ConanFile):
    name = "foo"
    version = "1.0.0"
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def build(self):
        self.output.info("new foo")
    """

    conanfile_foo_3 = """from conans import ConanFile
class Pkg(ConanFile):
    name = "qux"
    version = "1.0.0"
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def build(self):
        self.output.info("qux")
    """

    conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "foobar"
    version = "2.0"
    requires = "bar/0.1.0@foo/stable", "foo/1.0.0@bar/testing", "qux/1.0.0"

    def build(self):
        self.output.warn("BUILDING")
"""

    def setUp(self):
        self._ci_manager = MockCIManager()
        self._server = TestServer(users={"user": "password"},
                                  write_permissions=[("bar/0.1.0@foo/stable", "user"),
                                                     ("foo/1.0.0@bar/testing", "user"),
                                                     ("qux/1.0.0", "user")])
        self._client = TestClient(servers={"default": self._server},
                                  users={"default": [("user", "password")]})
        self._client.save({"conanfile_bar.py": self.conanfile_bar})
        self._client.run("export conanfile_bar.py foo/stable")
        self._client.save({"conanfile_foo.py": self.conanfile_foo})
        self._client.run("export conanfile_foo.py bar/testing")
        self._client.save({"conanfile_foo3.py": self.conanfile_foo_3})
        self._client.run("export conanfile_foo3.py")
        self._client.save({"conanfile.py": self.conanfile})

    def test_update_all_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "all",
                                 "CONAN_UPDATE_DEPENDENCIES": "True"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {})
            mulitpackager.run()

            self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploading packages for 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertIn("Uploading packages for 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertIn("Uploading packages for 'qux/1.0.0@'", self._client.out)

            # Upload new version of foo/1.0.0@bar/testing and re-add old revision in local cache
            self._client.save({"conanfile_foo.py": self.conanfile_foo_2})
            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager,
                                                      conanfile="conanfile_foo.py")
            mulitpackager.add({}, {})
            mulitpackager.run()

            self._client.run("remove -f foo/1.0.0@bar/testing")
            self._client.save({"conanfile_foo.py": self.conanfile_foo})
            self._client.run("export conanfile_foo.py bar/testing")

            # build again and update newest revision from remote
            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="missing",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {})
            mulitpackager.run()
            self.assertIn("foo/1.0.0@bar/testing: Package installed", self._client.out)
