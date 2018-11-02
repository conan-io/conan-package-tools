import platform
import unittest

from conans.client.tools import environment_append
from conans.test.utils.tools import TestClient, TestServer

from cpt.test.test_client.tools import get_patched_multipackager


class VisualToolsetsTest(unittest.TestCase):

    conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    settings = "os", "compiler"

    def build(self):
        self.output.warn("HALLO")
"""

    def test_toolsets_works(self):

        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_VISUAL_TOOLSETS": "15=v140;v140_xp,11=v140;v140_xp"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add_common_builds(reference="lib/1.0@user/stable",
                                            shared_option_name=False)
            mulitpackager.run()
            if platform.system() == "Windows":
                self.assertIn("Uploading package 1/4", tc.out)
                self.assertIn("Uploading package 2/4", tc.out)
                self.assertIn("Uploading package 3/4", tc.out)
                self.assertIn("Uploading package 4/4", tc.out)
                self.assertIn("compiler.toolset=v140", tc.out)
                self.assertIn("compiler.toolset=v140_xp", tc.out)
            else:
                self.assertIn("Uploading package 1/2", tc.out)
                self.assertIn("Uploading package 2/2", tc.out)

