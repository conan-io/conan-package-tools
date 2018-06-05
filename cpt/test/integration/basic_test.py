import os
import unittest
import sys

from conans import tools
from conans.model.ref import ConanFileReference

from cpt.test.integration.base import BaseTest
from cpt.packager import ConanMultiPackager
from cpt.test.unit.utils import MockCIManager


class SimpleTest(BaseTest):

    def test_missing_full_reference(self):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    pass
"""
        self.save_conanfile(conanfile)
        mp = ConanMultiPackager(username="lasote")
        with self.assertRaisesRegexp(Exception, "Specify a CONAN_REFERENCE or name and version"):
            mp.add_common_builds()

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
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
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
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                           "lasote", "mychannel",
                                           visual_versions=[15],
                                           archs=["x86"],
                                           build_types=["Release"],
                                           visual_runtimes=["MD"],
                                           exclude_vcvars_precommand=True,
                                           reference="zlib/1.2.2")
        self.packager.add_common_builds()
        self.packager.run_builds(1, 1)

    def test_shared_option_auto_managed(self):
        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}

"""
        self.save_conanfile(conanfile)
        self.packager = ConanMultiPackager(username="lasote")
        self.packager.add_common_builds()
        self.assertIn("lib:shared", self.packager.items[0].options)

        # Even without name and version but reference
        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}


"""
        self.save_conanfile(conanfile)
        self.packager = ConanMultiPackager(username="lasote", reference="lib2/1.0")
        self.packager.add_common_builds()
        self.assertIn("lib2:shared", self.packager.items[0].options)

        self.packager = ConanMultiPackager(username="lasote", reference="lib2/1.0")
        self.packager.add_common_builds(shared_option_name=False)
        self.assertNotIn("lib2:shared", self.packager.items[0].options)

    def test_exported_files(self):
        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    settings = "os"
    exports = "*"
    exports_sources = "source*"

"""
        ci_manager = MockCIManager()
        self.save_conanfile(conanfile)
        tools.save(os.path.join(self.tmp_folder, "other_file"), "Dummy contents")
        tools.save(os.path.join(self.tmp_folder, "source.cpp"), "Dummy contents")
        self.packager = ConanMultiPackager(username="lasote", reference="lib/1.0", ci_manager=ci_manager)
        self.packager.add({}, {}, {}, {})
        self.packager.run()

        pf = self.client_cache.export(ConanFileReference.loads("lib/1.0@lasote/testing"))
        found_in_export = False
        for exported in os.listdir(pf):
            if "other_file" == exported:
                found_in_export = True
                break

        self.assertTrue(found_in_export)

        pf = self.client_cache.export_sources(ConanFileReference.loads("lib/1.0@lasote/testing"))
        found_in_export_sources = False
        for exported in os.listdir(pf):
            if "source.cpp" == exported:
                found_in_export_sources = True
                break

        self.assertTrue(found_in_export_sources)

    def test_build_policy(self):
        ci_manager = MockCIManager(build_policy="outdated")
        conanfile = """from conans import ConanFile
import os

class Pkg(ConanFile):
    name = "lib"
    version = "1.2"
    settings = "os", "compiler", "build_type", "arch"

"""
        self.save_conanfile(conanfile)
        with tools.environment_append({"CONAN_USERNAME": "lasote"}):
            self.packager = ConanMultiPackager(channel="mychannel",
                                               gcc_versions=["6"],
                                               visual_versions=["12"],
                                               archs=["x86", "x86_64"],
                                               build_types=["Release"],
                                               ci_manager=ci_manager)
            self.packager.add_common_builds()
            self.packager.run()

