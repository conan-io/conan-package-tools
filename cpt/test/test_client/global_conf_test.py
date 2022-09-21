import unittest
import textwrap

from conans.client.tools import environment_append, load
from cpt.test.utils.tools import TestClient

from cpt.test.test_client.tools import get_patched_multipackager


class GlobalConfTest(unittest.TestCase):

    conanfile = textwrap.dedent("""
        from conans import ConanFile
        class Pkg(ConanFile):
            pass
        """)

    def test_environment_variable(self):
        tc = TestClient(users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        global_conf = ["tools.system.package_manager:mode=install", "tools.system.package_manager:sudo=True"]

        with environment_append({"CONAN_GLOBAL_CONF": ",".join(global_conf)}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add_common_builds(reference="lib/1.0@user/stable", shared_option_name=False)
            mulitpackager.run()
            assert textwrap.dedent("""tools.system.package_manager:mode=install
            tools.system.package_manager:sudo=True
            """.replace(" ", "")) == load(tc.cache.new_config_path)
