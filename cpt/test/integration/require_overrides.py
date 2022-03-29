import unittest

from cpt.test.utils.tools import TestClient
from cpt.test.test_client.tools import get_patched_multipackager


class RequireOverridesTest(unittest.TestCase):
    def test_require_overrides(self):
        conanfile_bar = """from conans import ConanFile
class Pkg(ConanFile):
    name = "bar"
    version = "0.1.0"

    def build(self):
        pass
        """

        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "foobar"
    version = "2.0"
    requires = "bar/0.1.0@foo/stable"

    def build(self):
        self.output.warn("BUILDING")
    """

        client = TestClient()
        client.save({"conanfile_bar.py": conanfile_bar})
        client.run("export conanfile_bar.py foo/stable")
        client.run("export conanfile_bar.py foo/testing")

        client.save({"conanfile.py": conanfile})
        mulitpackager = get_patched_multipackager(client, username="user",
                                                           channel="testing",
                                                           build_policy="missing",
                                                           require_overrides=["bar/0.1.0@foo/testing"],
                                                           exclude_vcvars_precommand=True)
        mulitpackager.add({}, {})
        mulitpackager.run()

        self.assertIn("requirement bar/0.1.0@foo/stable overridden by your conanfile to bar/0.1.0@foo/testing", client.out)
