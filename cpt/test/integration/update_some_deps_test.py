import unittest

from conans.client.tools import environment_append
from conans.test.utils.tools import TestClient, TestServer
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
    requires = "bar/0.1.0@foo/stable", "foo/1.0.0@bar/testing", "qux/1.0.0@qux/stable"

    def build(self):
        self.output.warn("BUILDING")
"""

    def setUp(self):
        self._ci_manager = MockCIManager()
        self._server = TestServer(users={"user": "password"},
                                  write_permissions=[("bar/0.1.0@foo/stable", "user"),
                                                     ("foo/1.0.0@bar/testing", "user"),
                                                     ("qux/1.0.0@qux/stable", "user")])
        self._client = TestClient(servers={"default": self._server},
                                  users={"default": [("user", "password")]})
        self._client.save({"conanfile_bar.py": self.conanfile_bar})
        self._client.run("export conanfile_bar.py foo/stable")
        self._client.save({"conanfile_foo.py": self.conanfile_foo})
        self._client.run("export conanfile_foo.py bar/testing")
        self._client.save({"conanfile_foo3.py": self.conanfile_foo_3})
        self._client.run("export conanfile_foo3.py qux/stable")
        self._client.save({"conanfile.py": self.conanfile})

    def test_update_some_dependencies(self):
        with environment_append({"CONAN_UPLOAD":  self._server.fake_url,
                                 "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_UPLOAD_DEPENDENCIES": "all",
                                 "CONAN_UPDATE_DEPENDENCIES": "True"}):

            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy=["foobar", "bar", "foo", "qux"],
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager)
            mulitpackager.add({}, {})
            mulitpackager.run()

            self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", self._client.out)
            self.assertIn("Uploading packages for 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertIn("Uploading packages for 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertIn("Uploading packages for 'qux/1.0.0@qux/stable'", self._client.out)

            # only build and upload foobar
            mulitpackager = get_patched_multipackager(self._client, username="user",
                                                      channel="testing",
                                                      build_policy="foobar",
                                                      exclude_vcvars_precommand=True,
                                                      ci_manager=self._ci_manager,
                                                      conanfile="conanfile.py")
            mulitpackager.add({}, {})
            mulitpackager.run()
            self.assertRegexpMatches(str(self._client.out), r'bar/0.1.0@foo/stable:.* - Cache')
            self.assertRegexpMatches(str(self._client.out), r'foo/1.0.0@bar/testing:.* - Cache')
            self.assertRegexpMatches(str(self._client.out), r'qux/1.0.0@qux/stable:.* - Cache')

            self.assertRegexpMatches(str(self._client.out), r'foobar/2.0@user/testing:.* - Build')

            self.assertIn("Uploading packages for 'foobar/2.0@user/testing'", self._client.out)
            self.assertNotIn("Uploading packages for 'bar/0.1.0@foo/stable'", self._client.out)
            self.assertNotIn("Uploading packages for 'foo/1.0.0@bar/testing'", self._client.out)
            self.assertNotIn("Uploading packages for 'qux/1.0.0@qux/stable'", self._client.out)



