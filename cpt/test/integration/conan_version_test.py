import unittest
from cpt.packager import ConanMultiPackager


class ConanVersionTest(unittest.TestCase):

    def test_conan_incompatible_version(self):
        cpt = ConanMultiPackager(username="user", reference="lib/1.0@conan/stable")
        cpt._newest_supported_conan_version = "2.0"
        cpt._client_conan_version = "2.1"
        with self.assertRaisesRegexp(Exception, "Conan/CPT version mismatch. "
                                                "Conan version installed: 2.1 . "
                                                "This version of CPT supports only Conan < 2.0"):
            cpt.run()

        cpt._newest_supported_conan_version = "2.1"
        cpt._client_conan_version = "2.1"
        cpt.run()
