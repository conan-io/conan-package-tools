import os
import platform
import unittest
import sys

from collections import defaultdict

from cpt.builds_generator import BuildConf
from cpt.packager import ConanMultiPackager
from conans import tools
from cpt.test.utils.tools import TestBufferConanOutput
from conans.model.ref import ConanFileReference
from cpt.test.unit.utils import MockConanAPI, MockRunner, MockCIManager


def platform_mock_for(so):
    class PlatformInfoMock(object):
        def system(self):
            return so
    return PlatformInfoMock()


class AppTest(unittest.TestCase):

    def setUp(self):
        self.runner = MockRunner()
        self.conan_api = MockConanAPI()
        self.ci_manager = MockCIManager()
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           reference="lib/1.0",
                                           ci_manager=self.ci_manager)

        for provider in ["APPVEYOR", "TRAVIS", "GITHUB_ACTIONS"]:
            if provider in os.environ:
                del os.environ[provider]

    def _add_build(self, number, compiler=None, version=None):
        self.packager.add({"os": "os%d" % number, "compiler": compiler or "compiler%d" % number,
                           "compiler.version": version or "4.3"},
                          {"option%d" % number: "value%d" % number,
                           "option%d" % number: "value%d" % number})

    def test_remove_build_if(self):
        self.packager.add({"arch": "x86", "build_type": "Release", "compiler": "gcc", "compiler.version": "6"})
        self.packager.add({"arch": "x86", "build_type": "Debug", "compiler": "gcc", "compiler.version": "6"})
        self.packager.add({"arch": "x86", "build_type": "Release", "compiler": "gcc", "compiler.version": "7"})
        self.packager.add({"arch": "x86", "build_type": "Debug", "compiler": "gcc", "compiler.version": "7"})

        self.packager.remove_build_if(lambda build: build.settings["compiler.version"] == "6")

        packager_expected = ConanMultiPackager("lasote", "mychannel",
                                               runner=self.runner,
                                               conan_api=self.conan_api,
                                               reference="lib/1.0",
                                               ci_manager=self.ci_manager)

        packager_expected.add({"arch": "x86", "build_type": "Release", "compiler": "gcc", "compiler.version": "7"})
        packager_expected.add({"arch": "x86", "build_type": "Debug", "compiler": "gcc", "compiler.version": "7"})

        self.assertEqual([tuple(a) for a in self.packager.items], packager_expected.items)

    def test_update_build_if(self):
        self.packager.add({"os": "Windows"})
        self.packager.add({"os": "Linux"})

        self.packager.update_build_if(lambda build: build.settings["os"] == "Windows",
                                      new_build_requires={"*": ["7zip/19.00"]})

        packager_expected = ConanMultiPackager("lasote", "mychannel",
                                               runner=self.runner,
                                               conan_api=self.conan_api,
                                               reference="lib/1.0",
                                               ci_manager=self.ci_manager)

        packager_expected.add({"os": "Windows"}, {}, {}, {"*": ["7zip/19.00"]})
        packager_expected.add({"os": "Linux"})

        self.assertEqual([tuple(a) for a in self.packager.items], packager_expected.items)

    def test_add_common_builds_update_build_if(self):
        self.packager.add_common_builds()
        self.packager.update_build_if(lambda build: build.settings["build_type"] == "Debug",
                                      new_options={"foo:bar": True})
        self.packager.update_build_if(lambda build: build.settings["build_type"] == "Release",
                                      new_options={"foo:qux": False})

        for settings, options, _, _, _ in self.packager.items:
            if settings["build_type"] == "Release":
                self.assertEqual(options, {"foo:qux": False})
            else:
                self.assertEqual(options, {"foo:bar": True})

    def test_full_profile(self):
        self.packager.add({"os": "Windows", "compiler": "gcc"},
                          {"option1": "One"},
                          {"VAR_1": "ONE",
                           "VAR_2": "TWO"},
                          {"*": ["myreference/1.0@lasote/testing"]})
        self.packager.run_builds(1, 1)
        profile = self.conan_api.get_profile_from_call_index(1)
        self.assertEquals(profile.settings["os"], "Windows")
        self.assertEquals(profile.settings["compiler"], "gcc")
        self.assertEquals(profile.options.as_list(), [("option1", "One")])
        self.assertEquals(profile.env_values.data[None]["VAR_1"], "ONE")
        self.assertEquals(profile.env_values.data[None]["VAR_2"], "TWO")
        self.assertEquals(profile.build_requires["*"],
                          [ConanFileReference.loads("myreference/1.0@lasote/testing")])

    def test_profile_environ(self):
        self.packager.add({"os": "Windows", "compiler": "gcc"},
                          {"option1": "One"},
                          {"VAR_1": "ONE",
                           "VAR_2": "TWO"},
                          {"*": ["myreference/1.0@lasote/testing"]})
        with tools.environment_append({"CONAN_BUILD_REQUIRES": "br1/1.0@conan/testing"}):
            self.packager.run_builds(1, 1)
            profile = self.conan_api.get_profile_from_call_index(1)
            self.assertEquals(profile.build_requires["*"],
                              [ConanFileReference.loads("myreference/1.0@lasote/testing"),
                               ConanFileReference.loads("br1/1.0@conan/testing")])

    def test_pages(self):
        for number in range(10):
            self._add_build(number)

        # 10 pages, 1 per build
        self.packager.run_builds(1, 10)
        self.conan_api.assert_tests_for([0])

        # 2 pages, 5 per build
        self.conan_api.reset()
        self.packager.run_builds(1, 2)
        self.conan_api.assert_tests_for([0, 2, 4, 6, 8])

        self.conan_api.reset()
        self.packager.run_builds(2, 2)
        self.conan_api.assert_tests_for([1, 3, 5, 7, 9])

        # 3 pages, 4 builds in page 1 and 3 in the rest of pages
        self.conan_api.reset()
        self.packager.run_builds(1, 3)
        self.conan_api.assert_tests_for([0, 3, 6, 9])

        self.conan_api.reset()
        self.packager.run_builds(2, 3)
        self.conan_api.assert_tests_for([1, 4, 7])

        self.conan_api.reset()
        self.packager.run_builds(3, 3)
        self.conan_api.assert_tests_for([2, 5, 8])

    def test_deprecation_gcc(self):

        with self.assertRaisesRegexp(Exception, "DEPRECATED GCC MINOR VERSIONS!"):
            ConanMultiPackager(username="lasote",
                               channel="mychannel",
                               runner=self.runner,
                               conan_api=self.conan_api,
                               gcc_versions=["4.3", "5.4"],
                               use_docker=True,
                               reference="zlib/1.2.11",
                               ci_manager=self.ci_manager)

    def test_32bits_images(self):
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      runner=self.runner,
                                      use_docker=True,
                                      docker_32_images=True,
                                      reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertIn("docker pull conanio/gcc6-x86", self.runner.calls[0])

        self.runner.reset()
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      use_docker=True,
                                      docker_32_images=False,
                                      reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertNotIn("docker pull conanio/gcc6-i386", self.runner.calls[0])

        self.runner.reset()
        with tools.environment_append({"CONAN_DOCKER_32_IMAGES": "1"}):
            packager = ConanMultiPackager(username="lasote",
                                          channel="mychannel",
                                          runner=self.runner,
                                          conan_api=self.conan_api,
                                          use_docker=True,
                                          reference="zlib/1.2.11",
                                          ci_manager=self.ci_manager)

            packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
            packager.run_builds(1, 1)
            self.assertIn("docker pull conanio/gcc6-x86", self.runner.calls[0])

        self.runner.reset()
        # Test the opossite
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      use_docker=True,
                                      docker_32_images=False,
                                      reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertIn("docker pull conanio/gcc6", self.runner.calls[0])

    def test_docker_gcc(self):
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           gcc_versions=["4.3", "5"],
                                           use_docker=True,
                                           reference="zlib/1.2.11",
                                           ci_manager=self.ci_manager)
        self._add_build(1, "gcc", "4.3")
        self._add_build(2, "gcc", "4.3")
        self._add_build(3, "gcc", "4.3")

        self.packager.run_builds(1, 2)
        self.assertIn("docker pull conanio/gcc43", self.runner.calls[0])
        self.assertIn('docker run ', self.runner.calls[1])
        self.assertNotIn('sudo pip', self.runner.calls[1])
        self.assertIn('pip install', self.runner.calls[1])
        self.assertIn('os=os1', self.runner.calls[4])
        self.packager.run_builds(1, 2)
        self.assertIn("docker pull conanio/gcc43", self.runner.calls[0])

        # Next build from 4.3 is cached, not pulls are performed
        self.assertIn('os=os3', self.runner.calls[5])

        for the_bool in ["True", "False"]:
            self.runner.reset()
            with tools.environment_append({"CONAN_DOCKER_USE_SUDO": the_bool}):
                self.packager = ConanMultiPackager(username="lasote",
                                                   channel="mychannel",
                                                   runner=self.runner,
                                                   conan_api=self.conan_api,
                                                   gcc_versions=["4.3", "5"],
                                                   use_docker=True,
                                                   reference="zlib/1.2.11",
                                                   ci_manager=self.ci_manager)
                self._add_build(1, "gcc", "4.3")
                self.packager.run_builds(1, 2)
                if the_bool == "True":
                    self.assertIn("sudo -E docker run", self.runner.calls[-1])
                else:
                    self.assertNotIn("sudo -E docker run", self.runner.calls[-1])
                    self.assertIn("docker run", self.runner.calls[-1])
            self.runner.reset()
            with tools.environment_append({"CONAN_PIP_USE_SUDO": the_bool}):
                self.packager = ConanMultiPackager(username="lasote",
                                                   channel="mychannel",
                                                   runner=self.runner,
                                                   conan_api=self.conan_api,
                                                   gcc_versions=["4.3", "5"],
                                                   use_docker=True,
                                                   reference="zlib/1.2.11",
                                                   ci_manager=self.ci_manager)
                self._add_build(1, "gcc", "4.3")
                self.packager.run_builds(1, 2)
                if the_bool == "True":
                    self.assertIn("sudo -E pip", self.runner.calls[1])
                else:
                    self.assertNotIn("sudo -E pip", self.runner.calls[1])
                    self.assertIn("pip", self.runner.calls[1])

    def test_docker_clang(self):
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           clang_versions=["3.8", "4.0"],
                                           use_docker=True,
                                           reference="zlib/1.2.11",
                                           ci_manager=self.ci_manager)

        self._add_build(1, "clang", "3.8")
        self._add_build(2, "clang", "3.8")
        self._add_build(3, "clang", "3.8")

        self.packager.run_builds(1, 2)
        self.assertIn("docker pull conanio/clang38", self.runner.calls[0])
        self.assertIn('docker run ', self.runner.calls[1])
        self.assertIn('os=os1', self.runner.calls[4])

        # Next build from 3.8 is cached, not pulls are performed
        self.assertIn('os=os3', self.runner.calls[5])

    def test_docker_gcc_and_clang(self):
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           gcc_versions=["5", "6"],
                                           clang_versions=["3.9", "4.0"],
                                           use_docker=True,
                                           reference="zlib/1.2.11",
                                           ci_manager=self.ci_manager)

        self._add_build(1, "gcc", "5")
        self._add_build(2, "gcc", "5")
        self._add_build(3, "gcc", "5")
        self._add_build(4, "clang", "3.9")
        self._add_build(5, "clang", "3.9")
        self._add_build(6, "clang", "3.9")

        self.packager.run_builds(1, 2)
        self.assertIn("docker pull conanio/gcc5", self.runner.calls[0])
        self.assertIn('docker run ', self.runner.calls[1])

        self.assertIn('os=os1', self.runner.calls[4])
        self.assertIn('os=os3', self.runner.calls[5])

        self.packager.run_builds(2, 2)
        self.assertIn("docker pull conanio/clang39", self.runner.calls[16])
        self.assertIn('docker run ', self.runner.calls[17])
        self.assertIn('os=os4', self.runner.calls[20])
        self.assertIn('os=os6', self.runner.calls[21])

    def test_upload_false(self):
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      upload=False, reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)
        self.assertFalse(packager._upload_enabled())

    def test_docker_env_propagated(self):
        # test env
        with tools.environment_append({"CONAN_FAKE_VAR": "32"}):
            self.packager = ConanMultiPackager(username="lasote",
                                               channel="mychannel",
                                               runner=self.runner,
                                               conan_api=self.conan_api,
                                               gcc_versions=["5", "6"],
                                               clang_versions=["3.9", "4.0"],
                                               use_docker=True,
                                               reference="zlib/1.2.11",
                                               ci_manager=self.ci_manager)
            self._add_build(1, "gcc", "5")
            self.packager.run_builds(1, 1)
            self.assertIn('-e CONAN_FAKE_VAR="32"', self.runner.calls[-1])

    def test_docker_home_env(self):
        with tools.environment_append({"CONAN_DOCKER_HOME": "/some/dir"}):
            self.packager = ConanMultiPackager(username="lasote",
                                               channel="mychannel",
                                               runner=self.runner,
                                               conan_api=self.conan_api,
                                               gcc_versions=["5", "6"],
                                               clang_versions=["3.9", "4.0"],
                                               use_docker=True,
                                               reference="zlib/1.2.11",
                                               ci_manager=self.ci_manager)
            self._add_build(1, "gcc", "5")
            self.packager.run_builds(1, 1)
            self.assertIn('-e CONAN_DOCKER_HOME="/some/dir"',
                          self.runner.calls[-1])
            self.assertEquals(self.packager.docker_conan_home, "/some/dir")

    def test_docker_home_opt(self):
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           gcc_versions=["5", "6"],
                                           clang_versions=["3.9", "4.0"],
                                           use_docker=True,
                                           docker_conan_home="/some/dir",
                                           reference="zlib/1.2.11",
                                           ci_manager=self.ci_manager)
        self._add_build(1, "gcc", "5")
        self.packager.run_builds(1, 1)
        self.assertEquals(self.packager.docker_conan_home, "/some/dir")

    def test_docker_invalid(self):
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           use_docker=True,
                                           reference="zlib/1.2.11",
                                           ci_manager=self.ci_manager)

        self._add_build(1, "msvc", "10")

        # Only clang and gcc have docker images
        self.assertRaises(Exception, self.packager.run_builds)

    def test_assign_builds_retrocompatibility(self):
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           gcc_versions=["4.3", "5"],
                                           use_docker=True,
                                           reference="lib/1.0",
                                           ci_manager=self.ci_manager)
        self.packager.add_common_builds()
        self.packager.builds = [({"os": "Windows"}, {"option": "value"})]
        self.assertEquals(self.packager.items, [BuildConf(settings={'os': 'Windows'},
                                                          options={'option': 'value'},
                                                          env_vars={}, build_requires={},
                                                          reference="lib/1.0@lasote/mychannel")])

    def test_only_mingw(self):

        mingw_configurations = [("4.9", "x86_64", "seh", "posix")]
        builder = ConanMultiPackager(mingw_configurations=mingw_configurations, visual_versions=[],
                                     username="Pepe", platform_info=platform_mock_for("Windows"),
                                     reference="lib/1.0", ci_manager=self.ci_manager)
        with tools.environment_append({"CONAN_SHARED_OPTION_NAME": "zlib:shared"}):
            builder.add_common_builds(pure_c=True)
        expected = [({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++",
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'arch': 'x86_64',
                      'build_type': 'Release', 'compiler': 'gcc'},
                     {'zlib:shared': False},
                     {},
                     {'*': [ConanFileReference.loads("mingw-w64/8.1")]}),
                    ({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++", 'arch': 'x86_64',
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'build_type': 'Debug',
                      'compiler': 'gcc'},
                     {'zlib:shared': False},
                     {},
                     {'*': [ConanFileReference.loads("mingw-w64/8.1")]}),

                    ({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++",
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'arch': 'x86_64',
                      'build_type': 'Release', 'compiler': 'gcc'},
                     {'zlib:shared': True},
                     {},
                     {'*': [ConanFileReference.loads("mingw-w64/8.1")]}),
                    ({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++", 'arch': 'x86_64',
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'build_type': 'Debug',
                      'compiler': 'gcc'},
                     {'zlib:shared': True},
                     {},
                     {'*': [ConanFileReference.loads("mingw-w64/8.1")]})]

        self.assertEquals([tuple(a) for a in builder.builds], expected)

    def test_named_pages(self):
        builder = ConanMultiPackager(username="Pepe", reference="zlib/1.2.11",
                                     ci_manager=self.ci_manager)
        named_builds = defaultdict(list)
        with tools.environment_append({"CONAN_SHARED_OPTION_NAME": "zlib:shared"}):
            builder.add_common_builds(pure_c=True)
            for settings, options, env_vars, build_requires, _ in builder.items:
                named_builds[settings['arch']].append([settings, options, env_vars, build_requires])
            builder.named_builds = named_builds

        self.assertEquals(builder.builds, [])
        if platform.system() == "Darwin":  # Not default x86 in Macos
            self.assertEquals(len(builder.named_builds), 1)
            self.assertFalse("x86" in builder.named_builds)
            self.assertTrue("x86_64" in builder.named_builds)
        else:
            self.assertEquals(len(builder.named_builds), 2)
            self.assertTrue("x86" in builder.named_builds)
            self.assertTrue("x86_64" in builder.named_builds)

    def test_remotes(self):
        runner = MockRunner()
        builder = ConanMultiPackager(username="Pepe",
                                     remotes=["url1", "url2"],
                                     runner=runner,
                                     conan_api=self.conan_api,
                                     reference="lib/1.0@lasote/mychannel",
                                     ci_manager=self.ci_manager)

        self.assertEquals(self.conan_api.calls[1].args[1], "url1")
        self.assertEquals(self.conan_api.calls[1].kwargs["insert"], -1)
        self.assertEquals(self.conan_api.calls[3].args[1], "url2")
        self.assertEquals(self.conan_api.calls[3].kwargs["insert"], -1)

        runner = MockRunner()
        self.conan_api = MockConanAPI()
        builder = ConanMultiPackager(username="Pepe",
                                     remotes="myurl1",
                                     runner=runner,
                                     conan_api=self.conan_api,
                                     reference="lib/1.0@lasote/mychannel",
                                     ci_manager=self.ci_manager)

        self.assertEquals(self.conan_api.calls[1].args[1], "myurl1")
        self.assertEquals(self.conan_api.calls[1].kwargs["insert"], -1)

        # Named remotes, with SSL flag
        runner = MockRunner()
        self.conan_api = MockConanAPI()
        remotes = [("u1", True, "my_cool_name1"),
                   ("u2", False, "my_cool_name2")]
        builder = ConanMultiPackager(username="Pepe",
                                     remotes=remotes,
                                     runner=runner,
                                     conan_api=self.conan_api,
                                     reference="lib/1.0@lasote/mychannel",
                                     ci_manager=self.ci_manager)

        self.assertEquals(self.conan_api.calls[1].args[0], "my_cool_name1")
        self.assertEquals(self.conan_api.calls[1].args[1], "u1")
        self.assertEquals(self.conan_api.calls[1].kwargs["insert"], -1)
        self.assertEquals(self.conan_api.calls[1].kwargs["verify_ssl"], True)

        self.assertEquals(self.conan_api.calls[3].args[0], "my_cool_name2")
        self.assertEquals(self.conan_api.calls[3].args[1], "u2")
        self.assertEquals(self.conan_api.calls[3].kwargs["insert"], -1)
        self.assertEquals(self.conan_api.calls[3].kwargs["verify_ssl"], False)

    def test_visual_defaults(self):

        with tools.environment_append({"CONAN_VISUAL_VERSIONS": "10"}):
            builder = ConanMultiPackager(username="Pepe",
                                         platform_info=platform_mock_for("Windows"),
                                         reference="lib/1.0@lasote/mychannel",
                                         ci_manager=self.ci_manager)
            builder.add_common_builds()
            for settings, _, _, _, _ in builder.items:
                self.assertEquals(settings["compiler"], "Visual Studio")
                self.assertEquals(settings["compiler.version"], "10")

        with tools.environment_append({"CONAN_VISUAL_VERSIONS": "10",
                                       "MINGW_CONFIGURATIONS": "4.9@x86_64@seh@posix"}):

            builder = ConanMultiPackager(username="Pepe",
                                         platform_info=platform_mock_for("Windows"),
                                         reference="lib/1.0@lasote/mychannel",
                                         ci_manager=self.ci_manager)
            builder.add_common_builds()
            for settings, _, _, _, _ in builder.items:
                self.assertEquals(settings["compiler"], "gcc")
                self.assertEquals(settings["compiler.version"], "4.9")

    def test_msvc_defaults(self):

        with tools.environment_append({"CONAN_MSVC_VERSIONS": "193",
                                       "CONAN_VISUAL_VERSIONS": ""}):
            builder = ConanMultiPackager(username="Pepe",
                                         platform_info=platform_mock_for("Windows"),
                                         reference="lib/1.0@lasote/mychannel",
                                         ci_manager=self.ci_manager)
            builder.add_common_builds()
            for settings, _, _, _, _ in builder.items:
                self.assertEquals(settings["compiler"], "msvc")
                self.assertEquals(settings["compiler.version"], "193")

        with tools.environment_append({"CONAN_MSVC_VERSIONS": "193",
                                       "CONAN_VISUAL_VERSIONS": "",
                                       "MINGW_CONFIGURATIONS": "4.9@x86_64@seh@posix"}):

            builder = ConanMultiPackager(username="Pepe",
                                         platform_info=platform_mock_for("Windows"),
                                         reference="lib/1.0@lasote/mychannel",
                                         ci_manager=self.ci_manager)
            builder.add_common_builds()
            for settings, _, _, _, _ in builder.items:
                self.assertEquals(settings["compiler"], "gcc")
                self.assertEquals(settings["compiler.version"], "4.9")

    def test_multiple_references(self):
        with tools.environment_append({"CONAN_REFERENCE": "zlib/1.2.8"}):
            builder = ConanMultiPackager(username="Pepe", ci_manager=self.ci_manager)
            builder.add_common_builds(reference="lib/1.0@lasote/mychannel")
            for _, _, _, _, reference in builder.items:
                self.assertEquals(str(reference), "lib/1.0@lasote/mychannel")
            builder.add_common_builds(reference="lib/2.0@lasote/mychannel")
            for _, _, _, _, reference in builder.items:
                self.assertTrue(str(reference) in ("lib/1.0@lasote/mychannel", "lib/2.0@lasote/mychannel"))

    def test_select_defaults_test(self):
        with tools.environment_append({"CONAN_REFERENCE": "zlib/1.2.8"}):
            builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                         gcc_versions=["4.8", "5"],
                                         username="foo",
                                         reference="lib/1.0@lasote/mychannel",
                                         ci_manager=self.ci_manager)

            self.assertEquals(builder.build_generator._clang_versions, [])

        with tools.environment_append({"CONAN_GCC_VERSIONS": "4.8, 5",
                                       "CONAN_REFERENCE": "zlib/1.2.8"}):
            builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                         username="foo",
                                         reference="lib/1.0@lasote/mychannel",
                                         ci_manager=self.ci_manager)

            self.assertEquals(builder.build_generator._clang_versions, [])
            self.assertEquals(builder.build_generator._gcc_versions, ["4.8", "5"])

        builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                     clang_versions=["4.8", "5"],
                                     username="foo",
                                     reference="lib/1.0",
                                     ci_manager=self.ci_manager)

        self.assertEquals(builder.build_generator._gcc_versions, [])

        with tools.environment_append({"CONAN_CLANG_VERSIONS": "4.8, 5",
                                       "CONAN_APPLE_CLANG_VERSIONS": " "}):
            builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                         username="foo",
                                         reference="lib/1.0",
                                         ci_manager=self.ci_manager)

            self.assertEquals(builder.build_generator._gcc_versions, [])
            self.assertEquals(builder.build_generator._clang_versions, ["4.8", "5"])
            self.assertEquals(builder.build_generator._clang_versions, ["4.8", "5"])
            self.assertEquals(builder.build_generator._apple_clang_versions, [])

    def test_upload(self):
        runner = MockRunner()
        runner.output = "arepo: myurl"
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     conan_api=self.conan_api,
                                     remotes="myurl, otherurl",
                                     platform_info=platform_mock_for("Darwin"),
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()

        # Duplicated upload remote puts upload repo first (in the remotes order)
        self.assertEqual(self.conan_api.calls[1].args[0], 'upload_repo')
        self.assertEqual(self.conan_api.calls[3].args[0], 'remote1')

        # Now check that the upload remote order is preserved if we specify it in the remotes
        runner = MockRunner()
        self.conan_api = MockConanAPI()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     conan_api=self.conan_api,
                                     remotes="otherurl, myurl, moreurl",
                                     platform_info=platform_mock_for("Darwin"),
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()

        self.assertEqual(self.conan_api.calls[1].args[0], 'remote0')
        self.assertEqual(self.conan_api.calls[3].args[0], 'upload_repo')
        self.assertEqual(self.conan_api.calls[5].args[0], 'remote2')

        runner = MockRunner()
        self.conan_api = MockConanAPI()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     conan_api=self.conan_api,
                                     remotes="otherurl",
                                     platform_info=platform_mock_for("Darwin"),
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()

        self.assertEqual(self.conan_api.calls[1].args[0], 'remote0')
        self.assertEqual(self.conan_api.calls[3].args[0], 'upload_repo')

    def test_build_policy(self):
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=self.runner,
                                     conan_api=self.conan_api,
                                     remotes="otherurl",
                                     platform_info=platform_mock_for("Darwin"),
                                     build_policy="outdated",
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()
        self.assertEquals(["outdated"], self.conan_api.calls[-1].kwargs["build_modes"])

    def test_multiple_build_policy(self):
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=self.runner,
                                     conan_api=self.conan_api,
                                     remotes="otherurl",
                                     platform_info=platform_mock_for("Darwin"),
                                     build_policy=["Hello", "outdated"],
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()
        self.assertEquals(["Hello", "outdated"], self.conan_api.calls[-1].kwargs["build_modes"])


        for build_policy, expected in [("missing", ["missing"]), ("all",[]), ("Hello,missing", ["Hello", "missing"])]:
            with tools.environment_append({"CONAN_BUILD_POLICY": build_policy}):
                self.conan_api = MockConanAPI()
                builder = ConanMultiPackager(username="pepe", channel="testing",
                                             reference="Hello/0.1", password="password",
                                             visual_versions=[], gcc_versions=[],
                                             apple_clang_versions=[],
                                             runner=self.runner,
                                             conan_api=self.conan_api,
                                             remotes="otherurl",
                                             platform_info=platform_mock_for("Darwin"),
                                             build_policy=build_policy,
                                             ci_manager=self.ci_manager)
                builder.add_common_builds()
                builder.run()
                self.assertEquals(expected, self.conan_api.calls[-1].kwargs["build_modes"])

    def test_test_folder(self):
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=self.runner,
                                     conan_api=self.conan_api,
                                     remotes="otherurl",
                                     platform_info=platform_mock_for("Darwin"),
                                     test_folder="foobar",
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()
        self.assertEquals("foobar", self.conan_api.calls[-1].kwargs["test_folder"])

        with tools.environment_append({"CONAN_BUILD_POLICY": "missing"}):
            self.conan_api = MockConanAPI()
            builder = ConanMultiPackager(username="pepe", channel="testing",
                                         reference="Hello/0.1", password="password",
                                         visual_versions=[], gcc_versions=[],
                                         apple_clang_versions=[],
                                         runner=self.runner,
                                         conan_api=self.conan_api,
                                         remotes="otherurl",
                                         platform_info=platform_mock_for("Darwin"),
                                         build_policy=None,
                                         ci_manager=self.ci_manager)
            builder.add_common_builds()
            builder.run()
            self.assertEquals(None, self.conan_api.calls[-1].kwargs["test_folder"])

    def test_check_credentials(self):

        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=self.runner,
                                     conan_api=self.conan_api,
                                     platform_info=platform_mock_for("Darwin"),
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()

        # When activated, check credentials before to create the profiles
        self.assertEqual(self.conan_api.calls[2].name, 'authenticate')
        self.assertEqual(self.conan_api.calls[3].name, 'create_profile')

        self.conan_api = MockConanAPI()
        # If we skip the credentials check, the login will be performed just before the upload
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=self.runner,
                                     conan_api=self.conan_api,
                                     platform_info=platform_mock_for("Darwin"),
                                     skip_check_credentials=True,
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()
        self.assertNotEqual(self.conan_api.calls[2].name, 'authenticate')

        # No upload, no authenticate
        self.conan_api = MockConanAPI()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload=None, visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=self.runner,
                                     conan_api=self.conan_api,
                                     platform_info=platform_mock_for("Darwin"),
                                     skip_check_credentials=True,
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()
        for action in self.conan_api.calls:
            self.assertNotEqual(action.name, 'authenticate')
            self.assertNotEqual(action.name, 'upload')

    def channel_detector_test(self):

        for branch, expected_channel in [("testing", "a_channel"),
                                         ("dummy", "a_channel"),
                                         ("stabl", "a_channel"),
                                         ("stabl/something", "a_channel"),
                                         ("stable", "stable"),
                                         ("stable/something", "stable"),
                                         ("releas", "a_channel"),
                                         ("releas/something", "a_channel"),
                                         ("release", "stable"),
                                         ("release/something", "stable"),
                                         ("maste", "a_channel"),
                                         ("maste/something", "a_channel"),
                                         ("master", "stable"),
                                         ("main", "stable"),
                                         ("masterSomething", "a_channel"),
                                         ("master/something", "a_channel")]:
            builder = ConanMultiPackager(username="pepe",
                                         channel="a_channel",
                                         reference="lib/1.0",
                                         ci_manager=MockCIManager(current_branch=branch))

            self.assertEquals(builder.channel, expected_channel, "Not match for branch %s" % branch)

    def channel_detector_test_custom_branch_patterns(self):

        for branch, expected_channel in [("trunk", "stable"),
                                         ("trunk/something", "a_channel"),
                                         ("tags/something", "stable"),
                                         ("tagsSomething", "a_channel"),
                                         ("stable", "a_channel"),
                                         ("stable/something", "a_channel"),
                                         ("release", "a_channel"),
                                         ("release/something", "a_channel"),
                                         ("master", "a_channel")]:
            # test env var
            with tools.environment_append({"CONAN_STABLE_BRANCH_PATTERN": "trunk$ tags/.*"}):
                builder = ConanMultiPackager(username="pepe",
                                             channel="a_channel",
                                             reference="lib/1.0",
                                             ci_manager=MockCIManager(current_branch=branch))

                self.assertEquals(builder.channel, expected_channel, "Not match for branch %s" % branch)
            # test passing as argument
            builder = ConanMultiPackager(username="pepe",
                                         channel="a_channel",
                                         reference="lib/1.0",
                                         stable_branch_pattern="trunk$ tags/.*",
                                         ci_manager=MockCIManager(current_branch=branch))

            self.assertEquals(builder.channel, expected_channel, "Not match for branch %s" % branch)

    def test_pip_conanio_image(self):
        self.packager = ConanMultiPackager(username="lasote",
                                            channel="mychannel",
                                            runner=self.runner,
                                            conan_api=self.conan_api,
                                            gcc_versions=["4.3", "5"],
                                            use_docker=True,
                                            docker_image='conanio/gcc43',
                                            reference="zlib/1.2.11",
                                            ci_manager=self.ci_manager)
        self._add_build(1, "gcc", "4.3")
        self.packager.run_builds(1, 2)
        self.assertNotIn("sudo -E pip", self.runner.calls[1])
        self.assertIn("pip", self.runner.calls[1])

        self.runner.reset()
        self.packager = ConanMultiPackager(username="lasote",
                                            channel="mychannel",
                                            runner=self.runner,
                                            conan_api=self.conan_api,
                                            gcc_versions=["4.3", "5"],
                                            docker_image='conanio/gcc43',
                                            reference="zlib/1.2.11",
                                            ci_manager=self.ci_manager)
        self._add_build(1, "gcc", "4.3")
        self.packager.run_builds(1, 2)
        self.assertNotIn("sudo -E pip", self.runner.calls[1])
        self.assertIn("pip", self.runner.calls[1])


    @unittest.skipIf(sys.platform.startswith("win"), "Requires Linux")
    def test_pip_docker_sudo(self):
        self.packager = ConanMultiPackager(username="lasote",
                                            channel="mychannel",
                                            runner=self.runner,
                                            conan_api=self.conan_api,
                                            gcc_versions=["4.3", "5"],
                                            docker_image='foobar/gcc43',
                                            reference="zlib/1.2.11",
                                            ci_manager=self.ci_manager)
        self._add_build(1, "gcc", "4.3")
        self.packager.run_builds(1, 2)
        self.assertIn("sudo -E pip", self.runner.calls[1])

        self.runner.reset()
        with tools.environment_append({"CONAN_PIP_USE_SUDO": "True"}):
            self.packager = ConanMultiPackager(username="lasote",
                                                channel="mychannel",
                                                runner=self.runner,
                                                conan_api=self.conan_api,
                                                gcc_versions=["4.3", "5"],
                                                docker_image='conanio/gcc43',
                                                reference="zlib/1.2.11",
                                                ci_manager=self.ci_manager)
        self._add_build(1, "gcc", "4.3")
        self.packager.run_builds(1, 2)
        self.assertIn("sudo -E pip", self.runner.calls[1])

    def test_regular_pip_command(self):
        """ CPT Should call `pip` when CONAN_PIP_PACKAGE or CONAN_PIP_INSTALL are declared.
        """
        with tools.environment_append({"CONAN_USERNAME": "foobar",
                                       "CONAN_PIP_PACKAGE": "conan==1.0.0-dev",
                                       "CONAN_PIP_INSTALL": "foobar==0.1.0"}):
            output = TestBufferConanOutput()
            self.packager = ConanMultiPackager(username="lasote",
                                               channel="mychannel",
                                               reference="lib/1.0",
                                               ci_manager=self.ci_manager,
                                               out=output.write,
                                               conan_api=self.conan_api,
                                               runner=self.runner,
                                               exclude_vcvars_precommand=True)
            self.packager.add_common_builds()
            self.packager.run()
            self.assertIn("[pip_update]", output)
            self.assertIn(" pip install -q conan==1.0.0-dev", self.runner.calls)
            self.assertIn(" pip install -q foobar==0.1.0", self.runner.calls)

    def test_custom_pip_command(self):
        """ CPT should run custom `pip` path when CONAN_PIP_COMMAND is declared.
        """
        pip = "pip3" if tools.which("pip3") else "pip2"
        with tools.environment_append({"CONAN_USERNAME": "foobar",
                                       "CONAN_PIP_PACKAGE": "conan==0.1.0",
                                       "CONAN_PIP_INSTALL": "foobar==0.1.0",
                                       "CONAN_PIP_COMMAND": pip}):
            output = TestBufferConanOutput()
            self.packager = ConanMultiPackager(username="lasote",
                                               channel="mychannel",
                                               reference="lib/1.0",
                                               ci_manager=self.ci_manager,
                                               out=output.write,
                                               conan_api=self.conan_api,
                                               runner=self.runner,
                                               exclude_vcvars_precommand=True)
            self.packager.add_common_builds()
            self.packager.run()
            self.assertIn("[pip_update]", output)
            self.assertIn(" {} install -q conan==0.1.0".format(pip), self.runner.calls)
            self.assertIn(" {} install -q foobar==0.1.0".format(pip), self.runner.calls)

    def test_invalid_pip_command(self):
        """ CPT should not accept invalid `pip` command when CONAN_PIP_COMMAND is declared.
        """
        with tools.environment_append({"CONAN_USERNAME": "foobar",
                                       "CONAN_PIP_PACKAGE": "conan==0.1.0",
                                       "CONAN_PIP_COMMAND": "/bin/bash"}):
            output = TestBufferConanOutput()
            with self.assertRaises(Exception) as context:
                self.packager = ConanMultiPackager(username="lasote",
                                                channel="mychannel",
                                                reference="lib/1.0",
                                                ci_manager=self.ci_manager,
                                                out=output.write,
                                                conan_api=self.conan_api,
                                                runner=self.runner,
                                                exclude_vcvars_precommand=True)
                self.packager.add_common_builds()
                self.packager.run()

                self.assertTrue("CONAN_PIP_COMMAND: '/bin/bash' is not a valid pip command" in context.exception)
            self.assertNotIn("[pip_update]", output)

    def test_skip_recipe_export(self):

        def _check_create_calls(skip_recipe_export):
            not_export = "not_export"
            creates = self.conan_api.get_creates()
            if skip_recipe_export:
                # Only first call should export recipe
                self.assertFalse(self.assertFalse(creates[0].kwargs[not_export]))
                for call in creates[1:]:
                    self.assertTrue(call.kwargs[not_export])
            else:
                for call in creates:
                    self.assertFalse(call.kwargs[not_export])

        output = TestBufferConanOutput()
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      visual_versions=["17"],
                                      archs=["x86", "x86_64"],
                                      build_types=["Release"],
                                      reference="zlib/1.2.11",
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      ci_manager=self.ci_manager,
                                      out=output.write)
        packager.add_common_builds()
        packager.run()
        _check_create_calls(False)

        with tools.environment_append({"CONAN_SKIP_RECIPE_EXPORT": "True"}):
            self.conan_api.reset()
            packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      visual_versions=["17"],
                                      archs=["x86", "x86_64"],
                                      build_types=["Release"],
                                      reference="zlib/1.2.11",
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      ci_manager=self.ci_manager,
                                      out=output.write)

            packager.add_common_builds()
            packager.run()
            _check_create_calls(True)

        self.conan_api.reset()
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      visual_versions=["17"],
                                      archs=["x86", "x86_64"],
                                      build_types=["Release"],
                                      reference="zlib/1.2.11",
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      ci_manager=self.ci_manager,
                                      skip_recipe_export=True,
                                      out=output.write)
        packager.add_common_builds()
        packager.run()
        _check_create_calls(True)

    def test_skip_recipe_export_docker(self):

        def _check_run_calls(skip_recipe_export):
            env_var = '-e CPT_SKIP_RECIPE_EXPORT="True"'
            run_calls = [call for call in self.runner.calls if "docker run --rm" in call]
            if skip_recipe_export:
                # Only first call should export recipe
                self.assertNotIn(env_var, run_calls[0])
                for call in run_calls[1:]:
                    self.assertIn(env_var, call)
            else:
                for call in run_calls:
                    self.assertNotIn(env_var, call)

        output = TestBufferConanOutput()
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      gcc_versions=["9"],
                                      archs=["x86", "x86_64"],
                                      build_types=["Release"],
                                      reference="zlib/1.2.11",
                                      use_docker=True,
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      ci_manager=self.ci_manager,
                                      out=output.write)
        packager.add_common_builds()
        packager.run()
        _check_run_calls(False)

        with tools.environment_append({"CONAN_SKIP_RECIPE_EXPORT": "True"}):
            self.runner.reset()
            packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      gcc_versions=["9"],
                                      archs=["x86", "x86_64"],
                                      build_types=["Release"],
                                      reference="zlib/1.2.11",
                                      use_docker=True,
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      ci_manager=self.ci_manager,
                                      out=output.write)

            packager.add_common_builds()
            packager.run()
            _check_run_calls(True)

        self.runner.reset()
        packager = ConanMultiPackager(username="lasote",
                                      channel="mychannel",
                                      gcc_versions=["9"],
                                      archs=["x86", "x86_64"],
                                      build_types=["Release"],
                                      reference="zlib/1.2.11",
                                      use_docker=True,
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      ci_manager=self.ci_manager,
                                      skip_recipe_export=True,
                                      out=output.write)
        packager.add_common_builds()
        packager.run()
        _check_run_calls(True)

    def test_lockfile(self):
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=self.runner,
                                     conan_api=self.conan_api,
                                     remotes="otherurl",
                                     platform_info=platform_mock_for("Darwin"),
                                     lockfile="foobar.lock",
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        builder.run()
        self.assertEquals("foobar.lock", self.conan_api.calls[-1].kwargs["lockfile"])

        with tools.environment_append({"CONAN_LOCKFILE": "couse.lock"}):
            self.conan_api = MockConanAPI()
            builder = ConanMultiPackager(username="pepe", channel="testing",
                                         reference="Hello/0.1", password="password",
                                         visual_versions=[], gcc_versions=[],
                                         apple_clang_versions=[],
                                         runner=self.runner,
                                         conan_api=self.conan_api,
                                         remotes="otherurl",
                                         platform_info=platform_mock_for("Darwin"),
                                         build_policy=None,
                                         ci_manager=self.ci_manager)
            builder.add_common_builds()
            builder.run()
            self.assertEquals("couse.lock", self.conan_api.calls[-1].kwargs["lockfile"])

    def test_pure_c_env_var(self):

        builder = ConanMultiPackager(gcc_versions=["8"], archs=["x86_64"], build_types=["Release"],
                                     username="Pepe", channel="testing",
                                     reference="Hello/0.1",
                                     platform_info=platform_mock_for("Linux"),
                                     ci_manager=self.ci_manager)
        builder.add_common_builds()
        expected = [({'arch': 'x86_64', 'build_type': 'Release',
                      'compiler': 'gcc',
                      'compiler.version': '8'},
                     {},
                     {},
                     {})]
        self.assertEquals([tuple(a) for a in builder.builds], expected)

        builder.builds = []
        with tools.environment_append({"CONAN_PURE_C": "True"}):
            builder.add_common_builds()
        expected = [({'arch': 'x86_64', 'build_type': 'Release',
                      'compiler': 'gcc',
                      'compiler.version': '8'},
                     {},
                     {},
                     {})]
        self.assertEquals([tuple(a) for a in builder.builds], expected)

        builder.builds = []
        with tools.environment_append({"CONAN_PURE_C": "False"}):
            builder.add_common_builds()
        expected = [({'arch': 'x86_64', 'build_type': 'Release',
                      'compiler': 'gcc',
                      'compiler.version': '8',
                      'compiler.libcxx': "libstdc++"},
                     {},
                     {},
                     {}),
                    ({'arch': 'x86_64', 'build_type': 'Release',
                      'compiler': 'gcc',
                      'compiler.version': '8',
                      'compiler.libcxx': "libstdc++11"},
                     {},
                     {},
                     {})]
        self.assertEquals([tuple(a) for a in builder.builds], expected)

    def test_docker_cwd(self):
        cwd = os.path.join(os.getcwd(), 'subdir')
        self.packager = ConanMultiPackager(username="lasote",
                                           channel="mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           gcc_versions=["9"],
                                           use_docker=True,
                                           reference="zlib/1.2.11",
                                           ci_manager=self.ci_manager,
                                           cwd=cwd)

        self._add_build(1, "gcc", "9")
        self.packager.run_builds(1, 1)
        self.assertIn('docker run --rm -v "%s:%s/project"' % (cwd, self.packager.docker_conan_home), self.runner.calls[4])
