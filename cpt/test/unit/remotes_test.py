import unittest

from conans import tools
from cpt.printer import Printer
from cpt.remotes import RemotesManager
from cpt.test.unit.packager_test import MockConanAPI


class RemotesTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()

    def assert_serial_deserial(self, manager, expected):
        self.assertEquals(manager.env_vars(), expected)
        with tools.environment_append(expected):
            manager = RemotesManager(self.conan_api, Printer())
            self.assertEquals(manager.env_vars(), expected)

    def test_plain(self):
        manager = RemotesManager(self.conan_api, Printer(), remotes_input="url1, url", upload_input="url1")
        expected = {'CONAN_REMOTES': 'url1@True@remote0,url@True@remote1',
                    'CONAN_UPLOAD': 'url1@True@upload_repo'}
        self.assert_serial_deserial(manager, expected)

    def test_list(self):
        remotes_input = [("url1", True, "remote1"),
                         ("url2", False, "remote2")]
        upload_input = ("url3", True, "remote1")
        manager = RemotesManager(self.conan_api, Printer(), remotes_input=remotes_input,
                                 upload_input=upload_input)
        expected = {'CONAN_REMOTES': 'url1@True@remote1,url2@False@remote2',
                    'CONAN_UPLOAD': 'url3@True@remote1'}
        self.assert_serial_deserial(manager, expected)
