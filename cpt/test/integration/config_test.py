from cpt.printer import Printer
from cpt.config import ConfigManager
from cpt.test.integration.base import BaseTest
from conans.errors import ConanException


class RemotesTest(BaseTest):

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
