import unittest
import textwrap
from cpt.config import GlobalConf
from cpt.printer import Printer
from cpt.test.unit.packager_test import MockConanAPI
from conans import tools


class GlobalConfUnitTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()
        self.configuration = ["tools.system.package_manager:mode=install", "tools.system.package_manager:sudo=True"]

    def test_new_global_conf(self):
        manager = GlobalConf(self.conan_api, Printer())
        manager.populate(self.configuration)
        content = tools.load(self.conan_api._cache.new_config_path)
        assert content == textwrap.dedent("""tools.system.package_manager:mode=install
                                             tools.system.package_manager:sudo=True
                                          """.replace(" ", ""))

    def test_append_global_conf(self):
        manager = GlobalConf(self.conan_api, Printer())
        manager.populate(self.configuration)
        append_conf = ["tools.system.package_manager:tool=yum"]
        manager.populate(append_conf)
        content = tools.load(self.conan_api._cache.new_config_path)
        assert content == textwrap.dedent("""tools.system.package_manager:mode=install
                                             tools.system.package_manager:sudo=True
                                             tools.system.package_manager:tool=yum
                                          """.replace(" ", ""))

    def test_string_global_conf(self):
        configuration = "tools.system.package_manager:mode=install,tools.system.package_manager:sudo=True"
        manager = GlobalConf(self.conan_api, Printer())
        manager.populate(configuration)
        content = tools.load(self.conan_api._cache.new_config_path)
        assert content == textwrap.dedent("""tools.system.package_manager:mode=install
                                             tools.system.package_manager:sudo=True
                                          """.replace(" ", ""))
