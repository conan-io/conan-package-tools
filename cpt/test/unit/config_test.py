import unittest

from conans.errors import ConanException

from cpt.config import ConfigManager
from cpt.printer import Printer
from cpt.test.integration.base import BaseTest
from cpt.test.unit.packager_test import MockConanAPI


class RemotesTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()

    def test_valid_config(self):
        manager = ConfigManager(self.conan_api, Printer())
        manager.install('https://github.com/bincrafters/conan-config.git')


class RemotesTestRealApi(BaseTest):

    def test_valid_config(self):
        manager = ConfigManager(self.api, Printer())

        profiles = self.api.profile_list()
        self.assertEquals(len(profiles), 0)

        manager.install("https://github.com/bincrafters/conan-config.git")

        profiles = self.api.profile_list()
        self.assertGreater(len(profiles), 3)

    def test_invalid_config(self):
        manager = ConfigManager(self.api, Printer())

        profiles = self.api.profile_list()
        self.assertEquals(len(profiles), 0)

        try:
            manager.install("https://github.com/")
            self.fail("Could not accept wrong URL")
        except ConanException:
            pass