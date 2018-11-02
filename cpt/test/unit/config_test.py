import unittest

from cpt.printer import Printer
from cpt.config import ConfigManager
from cpt.test.unit.packager_test import MockConanAPI


class RemotesTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()

    def test_valid_config(self):
        manager = ConfigManager(self.conan_api, Printer())
        manager.install('https://github.com/bincrafters/conan-config.git')
