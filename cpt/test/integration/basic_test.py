import unittest

from future.moves import sys

from cpt.test.integration.base import BaseTest
from cpt.packager import ConanMultiPackager


class SimpleTest(BaseTest):

    def test_missing_full_reference(self):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    pass
"""
        self.save_conanfile(conanfile)
        with self.assertRaisesRegexp(Exception, "Specify a CONAN_REFERENCE or name and version"):
            ConanMultiPackager(username="lasote")

    def test_missing_username(self):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    options = {"shared": [True, False]}
    default_options = "shared=False"

"""
        self.save_conanfile(conanfile)

        with self.assertRaisesRegexp(Exception, "Instance ConanMultiPackage with 'username' "
                                                "parameter or use CONAN_USERNAME env variable"):
            ConanMultiPackager()

    @unittest.skipUnless(sys.platform.startswith("win"), "Requires Windows")
    def test_msvc(self):
        conanfile = """from conans import ConanFile
import os

class Pkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def build(self):
        assert("WindowsLibPath" in os.environ)

"""
        self.save_conanfile(conanfile)
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           visual_versions=[15],
                                           archs=["x86"],
                                           build_types=["Release"],
                                           visual_runtimes=["MD"],
                                           reference="zlib/1.2.2")
        self.packager.add_common_builds()
        self.packager.run_builds(1, 1)

    def test_msvc_exclude_precommand(self):
        conanfile = """from conans import ConanFile
import os

class Pkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def build(self):
        assert("WindowsLibPath" not in os.environ)

"""
        self.save_conanfile(conanfile)
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           visual_versions=[15],
                                           archs=["x86"],
                                           build_types=["Release"],
                                           visual_runtimes=["MD"],
                                           exclude_vcvars_precommand=True,
                                           reference="zlib/1.2.2")
        self.packager.add_common_builds()
        self.packager.run_builds(1, 1)
