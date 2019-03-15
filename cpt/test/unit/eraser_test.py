# -*- coding: utf-8 -*-
import unittest

from collections import namedtuple
from conans.test.utils.tools import TestBufferConanOutput
from cpt.eraser import Eraser
from cpt.printer import Printer
from cpt.test.unit.packager_test import MockConanAPI


class AuthTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()
        self.output = TestBufferConanOutput()
        self.printer = Printer(self.output.write)

    def test_invalid_remote(self):
        eraser = Eraser(self.conan_api, None, None, self.printer, True)
        eraser.remove_outdated_packages("foo/0.1.0@user/channel")
        self.assertIn("Remove outdated skipped, no remote available", self.output)
        self.assertFalse(self.conan_api.calls)

    def test_invalid_authentication(self):
        FakeRemoteManager = namedtuple("FakeRemoteManager", "upload_remote_name")
        remote_manager = FakeRemoteManager(upload_remote_name="default")
        eraser = Eraser(self.conan_api, remote_manager, None, self.printer, True)
        eraser.remove_outdated_packages("foo/0.1.0@user/channel")
        self.assertIn("Remove outdated skipped, credentials for remote 'default' not available", self.output)
        self.assertFalse(self.conan_api.calls)
