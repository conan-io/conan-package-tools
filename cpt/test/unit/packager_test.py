import os
import platform
import unittest

from collections import defaultdict

from cpt.builds_generator import BuildConf
from cpt.packager import ConanMultiPackager
from conans import tools
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
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           reference="lib/1.0",
                                           ci_manager=self.ci_manager)
        if "APPVEYOR" in os.environ:
            del os.environ["APPVEYOR"]
        if "TRAVIS" in os.environ:
            del os.environ["TRAVIS"]

    def _add_build(self, number, compiler=None, version=None):
        self.packager.add({"os": "os%d" % number, "compiler": compiler or "compiler%d" % number,
                           "compiler.version": version or "4.3"},
                          {"option%d" % number: "value%d" % number,
                           "option%d" % number: "value%d" % number})

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
            ConanMultiPackager(["--build missing", "-r conan.io"],
                               "lasote", "mychannel",
                               runner=self.runner,
                               conan_api=self.conan_api,
                               gcc_versions=["4.3", "5.4"],
                               use_docker=True,
                               reference="zlib/1.2.11",
                               ci_manager=self.ci_manager)

    def test_32bits_images(self):
        packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                      "lasote", "mychannel",
                                      runner=self.runner,
                                      use_docker=True,
                                      docker_32_images=True,
                                      reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertIn("docker pull lasote/conangcc6-x86", self.runner.calls[0])

        self.runner.reset()
        packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                      "lasote", "mychannel",
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      use_docker=True,
                                      docker_32_images=False,
                                      reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertNotIn("docker pull lasote/conangcc6-i386", self.runner.calls[0])

        self.runner.reset()
        with tools.environment_append({"CONAN_DOCKER_32_IMAGES": "1"}):
            packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                          "lasote", "mychannel",
                                          runner=self.runner,
                                          conan_api=self.conan_api,
                                          use_docker=True,
                                          reference="zlib/1.2.11",
                                          ci_manager=self.ci_manager)

            packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
            packager.run_builds(1, 1)
            self.assertIn("docker pull lasote/conangcc6-x86", self.runner.calls[0])

        self.runner.reset()
        # Test the opossite
        packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                      "lasote", "mychannel",
                                      runner=self.runner,
                                      conan_api=self.conan_api,
                                      use_docker=True,
                                      docker_32_images=False,
                                      reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertIn("docker pull lasote/conangcc6", self.runner.calls[0])

    def test_docker_gcc(self):
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                           "lasote", "mychannel",
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
        self.assertIn("docker pull lasote/conangcc43", self.runner.calls[0])
        self.assertIn('docker run ', self.runner.calls[1])
        self.assertIn('os=os1', self.runner.calls[4])
        self.packager.run_builds(1, 2)
        self.assertIn("docker pull lasote/conangcc43", self.runner.calls[0])

        # Next build from 4.3 is cached, not pulls are performed
        self.assertIn('os=os3', self.runner.calls[5])

        for the_bool in ["True", "False"]:
            self.runner.reset()
            with tools.environment_append({"CONAN_DOCKER_USE_SUDO": the_bool}):
                self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                                   "lasote", "mychannel",
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
                self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                                   "lasote", "mychannel",
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
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                           "lasote", "mychannel",
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
        self.assertIn("docker pull lasote/conanclang38", self.runner.calls[0])
        self.assertIn('docker run ', self.runner.calls[1])
        self.assertIn('os=os1', self.runner.calls[4])

        # Next build from 3.8 is cached, not pulls are performed
        self.assertIn('os=os3', self.runner.calls[5])

    def test_docker_gcc_and_clang(self):
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                           "lasote", "mychannel",
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
        self.assertIn("docker pull lasote/conangcc5", self.runner.calls[0])
        self.assertIn('docker run ', self.runner.calls[1])

        self.assertIn('os=os1', self.runner.calls[4])
        self.assertIn('os=os3', self.runner.calls[5])

        self.packager.run_builds(2, 2)
        self.assertIn("docker pull lasote/conanclang39", self.runner.calls[16])
        self.assertIn('docker run ', self.runner.calls[17])
        self.assertIn('os=os4', self.runner.calls[20])
        self.assertIn('os=os6', self.runner.calls[21])

    def test_upload_false(self):
        packager = ConanMultiPackager(["--build missing", "-r conan.io"], "lasote", "mychannel",
                                      upload=False, reference="zlib/1.2.11",
                                      ci_manager=self.ci_manager)
        self.assertFalse(packager._upload_enabled())

    def test_docker_env_propagated(self):
        # test env
        with tools.environment_append({"CONAN_FAKE_VAR": "32"}):
            self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                               "lasote", "mychannel",
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

    def test_docker_invalid(self):
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           conan_api=self.conan_api,
                                           use_docker=True,
                                           reference="zlib/1.2.11",
                                           ci_manager=self.ci_manager)

        self._add_build(1, "msvc", "10")

        # Only clang and gcc have docker images
        self.assertRaises(Exception, self.packager.run_builds)

    def test_assign_builds_retrocompatibility(self):
        self.packager = ConanMultiPackager(["--build missing", "-r conan.io"],
                                           "lasote", "mychannel",
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
        builder.add_common_builds(shared_option_name="zlib:shared", pure_c=True)
        expected = [({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++",
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'arch': 'x86_64',
                      'build_type': 'Release', 'compiler': 'gcc'},
                     {'zlib:shared': True},
                     {},
                     {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}),
                    ({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++", 'arch': 'x86_64',
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'build_type': 'Debug',
                      'compiler': 'gcc'},
                     {'zlib:shared': True},
                     {},
                     {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}),

                    ({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++",
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'arch': 'x86_64',
                      'build_type': 'Release', 'compiler': 'gcc'},
                     {'zlib:shared': False},
                     {},
                     {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}),
                    ({'compiler.exception': 'seh', 'compiler.libcxx': "libstdc++", 'arch': 'x86_64',
                      'compiler.threads': 'posix', 'compiler.version': '4.9', 'build_type': 'Debug',
                      'compiler': 'gcc'},
                     {'zlib:shared': False},
                     {},
                     {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]})]

        self.assertEquals([tuple(a) for a in builder.builds], expected)

    def test_named_pages(self):
        builder = ConanMultiPackager(username="Pepe", reference="zlib/1.2.11",
                                     ci_manager=self.ci_manager)
        named_builds = defaultdict(list)
        builder.add_common_builds(shared_option_name="zlib:shared", pure_c=True)
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

        builder.add({}, {}, {}, {})
        builder.run_builds()
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

        builder.add({}, {}, {}, {})
        builder.run_builds()
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

        builder.add({}, {}, {}, {})
        builder.run_builds()
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

    def select_defaults_test(self):
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

        with tools.environment_append({"CONAN_CLANG_VERSIONS": "4.8, 5"}):
            builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                         username="foo",
                                         reference="lib/1.0",
                                         ci_manager=self.ci_manager)

            self.assertEquals(builder.build_generator._gcc_versions, [])
            self.assertEquals(builder.build_generator._clang_versions, ["4.8", "5"])

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
                                         build_policy="missing",
                                         ci_manager=self.ci_manager)
            builder.add_common_builds()
            builder.run()
            self.assertEquals(["missing"], self.conan_api.calls[-1].kwargs["build_modes"])

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
        self.assertEqual(self.conan_api.calls[5].name, 'create_profile')

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
        self.assertNotEqual(self.conan_api.calls[0].name, 'authenticate')

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
                                         ("stable", "stable"),
                                         ("stable/something", "stable"),
                                         ("release", "stable"),
                                         ("release/something", "stable"),
                                         ("master", "stable"),
                                         ("master/something", "a_channel")]:
            builder = ConanMultiPackager(username="pepe",
                                         channel="a_channel",
                                         reference="lib/1.0",
                                         ci_manager=MockCIManager(current_branch=branch))

            self.assertEquals(builder.channel, expected_channel, "Not match for branch %s" % branch)
