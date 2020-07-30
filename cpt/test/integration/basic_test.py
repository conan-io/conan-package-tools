import os
import unittest
import sys
import json

from conans import tools
from conans.model.ref import ConanFileReference
from conans.errors import ConanException

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
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
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
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
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

    def test_auto_managed_subdirectory(self):
        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}

"""
        cwd = os.path.join(self.tmp_folder, "subdirectory")
        tools.save(os.path.join(cwd, "conanfile.py"), conanfile)
        self.packager = ConanMultiPackager(username="lasote", cwd=cwd)
        self.packager.add_common_builds()
        self.assertGreater(len(self.packager.items), 0)
        self.assertIn("lib:shared", self.packager.items[0].options)

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

        ref = ConanFileReference.loads("lib/1.0@lasote/testing")
        pf = self.client_cache.package_layout(ref).export()
        found_in_export = False
        for exported in os.listdir(pf):
            if "other_file" == exported:
                found_in_export = True
                break

        self.assertTrue(found_in_export)

        pf = self.client_cache.package_layout(ref).export_sources()
        found_in_export_sources = False
        for exported in os.listdir(pf):
            if "source.cpp" == exported:
                found_in_export_sources = True
                break

        self.assertTrue(found_in_export_sources)

    def test_build_policy(self):
        ci_manager = MockCIManager()
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
                                               build_policy="outdated",
                                               ci_manager=ci_manager)
            self.packager.add_common_builds()
            self.packager.run()

        with tools.environment_append({"CONAN_USERNAME": "lasote",
                                       "CONAN_BUILD_POLICY": "outdated"}):
            self.packager = ConanMultiPackager(channel="mychannel",
                                               gcc_versions=["6"],
                                               visual_versions=["12"],
                                               archs=["x86", "x86_64"],
                                               build_types=["Release"],
                                               ci_manager=ci_manager)
            self.packager.add_common_builds()
            self.packager.run()

    def test_multiple_build_policy(self):
        ci_manager = MockCIManager()
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
                                               build_policy=["cascade", "outdated"],
                                               ci_manager=ci_manager)
            self.packager.add_common_builds()
            self.packager.run()

        with tools.environment_append({"CONAN_USERNAME": "lasote",
                                       "CONAN_BUILD_POLICY": "outdated, lib"}):
            self.packager = ConanMultiPackager(channel="mychannel",
                                               gcc_versions=["6"],
                                               visual_versions=["12"],
                                               archs=["x86", "x86_64"],
                                               build_types=["Release"],
                                               ci_manager=ci_manager)
            self.packager.add_common_builds()
            self.packager.run()

    def test_custom_conanfile(self):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.2"
    settings = "os", "compiler", "build_type", "arch"
"""
        tools.save(os.path.join(self.tmp_folder, "foobar.py"), conanfile)
        with tools.environment_append({"CONAN_CONANFILE": "foobar.py"}):
            self.packager = ConanMultiPackager(username="pepe",
                                               channel="mychannel",
                                               out=self.output.write)
            self.packager.add({}, {}, {}, {})
            self.packager.run()
        self.assertIn("conanfile                 | foobar.py", self.output)

        tools.save(os.path.join(self.tmp_folder, "custom_recipe.py"), conanfile)
        self.packager = ConanMultiPackager(username="pepe",
                                           channel="mychannel",
                                           conanfile="custom_recipe.py",
                                           out=self.output.write)
        self.packager.add({}, {}, {}, {})
        self.packager.run()
        self.assertIn("conanfile                 | custom_recipe.py", self.output)

    def test_partial_reference(self):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "foobar"
    version = "0.1.0"

    def configure(self):
        self.output.info("hello all")
"""
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)
        with tools.environment_append({"CONAN_REFERENCE": "foobar/0.1.0@"}):
            self.packager = ConanMultiPackager(out=self.output.write)
            self.packager.add({}, {}, {}, {})
            self.packager.run()
        self.assertIn("partial_reference         | foobar/0.1.0@", self.output)

        self.packager = ConanMultiPackager(out=self.output.write)
        self.packager.add({}, {}, {}, {})
        self.packager.run()
        self.assertIn("partial_reference         | foobar/0.1.0@", self.output)

    def test_save_packages_summary(self):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "foobar"
    version = "0.1.0"

    def configure(self):
        self.output.info("hello all")
"""
        json_file = 'cpt_summary_file.json'
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)
        self.packager = ConanMultiPackager(out=self.output.write)
        self.packager.add({}, {}, {}, {})
        self.packager.run(summary_file=json_file)
        self.assertTrue(os.path.isfile(json_file))
        with open(json_file) as json_content:
            json_data = json.load(json_content)
            self.assertFalse(json_data[0]["package"]["error"])

        json_file = "_" + json_file
        self.packager = ConanMultiPackager(out=self.output.write)
        self.packager.add({}, {}, {}, {})
        self.packager.run()
        self.packager.save_packages_summary(json_file)
        self.assertTrue(os.path.isfile(json_file))
        with open(json_file) as json_content:
            json_data = json.load(json_content)
            self.assertFalse(json_data[0]["package"]["error"])

        json_file = "__" + json_file
        with tools.environment_append({"CPT_SUMMARY_FILE": json_file}):
            self.packager = ConanMultiPackager(out=self.output.write)
            self.packager.add({}, {}, {}, {})
            self.packager.run()
            self.assertTrue(os.path.isfile(json_file))
            with open(json_file) as json_content:
                json_data = json.load(json_content)
                self.assertFalse(json_data[0]["package"]["error"])

    def test_disable_test_folder(self):
        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
"""
        self.save_conanfile(conanfile)
        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    def test(self):
        raise Exception("Should not run")
"""
        tools.save(os.path.join(self.tmp_folder, "test_package", "conanfile.py"), conanfile)
        with tools.environment_append({"CPT_TEST_FOLDER": "False"}):
            self.packager = ConanMultiPackager(out=self.output.write)
            self.packager.add_common_builds()
            self.packager.run()

    def test_invalid_test_folder(self):
        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
"""
        self.save_conanfile(conanfile)
        for test_folder in ["True", "foobar"]:
            with tools.environment_append({"CPT_TEST_FOLDER": test_folder}):
                self.packager = ConanMultiPackager(out=self.output.write)
                self.packager.add_common_builds()
                with self.assertRaises(ConanException) as raised:
                    self.packager.run()
                    self.assertIn("test folder '{}' not available, or it doesn't have a conanfile.py"
                                  .format(test_folder),
                                  str(raised.exception))

    def test_custom_name_version(self):
        conanfile = """from conans import ConanFile
from datetime import date
class Pkg(ConanFile):

    def configure(self):
        self.output.info("hello all")

    def set_name(self):
        self.name = "foobar"

    def set_version(self):
        today = date.today()
        self.version = today.strftime("%Y%B%d")
"""
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)
        self.packager = ConanMultiPackager(out=self.output.write)
        self.packager.add_common_builds(pure_c=False)
        self.packager.run()

    def test_header_only_option_true(self):
        header_only = self._test_header_only(False)
        self.assertEqual(header_only, 1)
        self.packager.run()

    def test_header_only_option_false(self):
        header_only = self._test_header_only(True)
        self.assertEqual(header_only, int(len(self.packager.builds) / 2))
        self.packager.run()

    def _test_header_only(self, default_value):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "qux"
    version = "0.1.0"
    settings = "os"
    options = {"header_only": [True, False], "shared": [True, False], "fPIC": [True, False]}
    default_options = {"header_only": %s, "shared": False, "fPIC": True}

    def configure(self):
        if self.options.header_only:
            del self.options.shared
            del self.options.fPIC

    def package_id(self):
        if self.options.header_only:
            self.info.header_only()
""" % default_value
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)
        self.packager = ConanMultiPackager(out=self.output.write)
        self.packager.add_common_builds(pure_c=False)

        header_only = 0
        for build in self.packager.builds:
            _, options, _, _ = build
            if options.get("qux:header_only") == (not default_value):
                header_only += 1
        return header_only

    def test_build_all_option_values(self):
        conanfile = """from conans import ConanFile
class Pkg(ConanFile):
    name = "qux"
    version = "0.1.0"
    options = {"shared": [True, False], "fPIC": [True, False],
               "header_only": [True, False], "foo": [True, False],
               "bar": ["baz", "qux", "foobar"], "blah": "ANY"}
    default_options = {"shared": False, "fPIC": True, "header_only": False,
                       "foo": False, "bar": "baz", "blah": 42}

    def configure(self):
        self.output.info("hello all")
"""
        tools.save(os.path.join(self.tmp_folder, "conanfile.py"), conanfile)
        self.packager = ConanMultiPackager(out=self.output.write)
        self.packager.add_common_builds(pure_c=False, build_all_options_values=["qux:foo", "qux:bar", "qux:blah"])
        self.packager.run()