import os
import sys
import unittest

from collections import defaultdict

from conan.builds_generator import BuildConf
from conan.packager import ConanMultiPackager
from conans import tools
from conans.model.ref import ConanFileReference
from conans.util.files import load
from conans.model.profile import Profile


def platform_mock_for(so):
     class PlatformInfoMock(object):
        def system(self):
            return so
     return PlatformInfoMock()


class MockRunner(object):

    def __init__(self):
        self.reset()
        self.output = ""

    def reset(self):
        self.calls = []

    def __call__(self, command):
        self.calls.append(command)
        return 0

    def get_profile_from_trace(self, number):
        call = self.calls[number]
        profile_start = call.find("--profile") + 10
        end_profile = call[profile_start:].find(" ") + profile_start
        profile_path = call[profile_start: end_profile]
        if hasattr(Profile, "loads"):  # retrocompatibility
            return Profile.loads(load(profile_path))
        else:
            from conans.client.profile_loader import read_profile
            tools.replace_in_file(profile_path, "include", "#include")
            # FIXME: Not able to load here the default
            return read_profile(profile_path, os.path.dirname(profile_path), None)[0]

    def assert_tests_for(self, numbers):
        """Check if executor has ran the builds that are expected.
        numbers are integers"""
        def assert_profile_for(pr, num):
            assert(pr.settings["compiler"] == 'compiler%d' % num)
            assert(pr.settings["os"] == 'os%d' % num)
            assert(pr.options.as_list() == [('option%d' % num, 'value%d' % num)])

        testp_counter = 0
        for i, call in enumerate(self.calls):
            if call.startswith("conan create"):
                profile = self.get_profile_from_trace(i)
                assert_profile_for(profile, numbers[testp_counter])
                testp_counter += 1


class AppTest(unittest.TestCase):

    def setUp(self):
        self.runner = MockRunner()
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner)
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
        profile = self.runner.get_profile_from_trace(0)
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
            profile = self.runner.get_profile_from_trace(0)
            self.assertEquals(profile.build_requires["*"],
                              [ConanFileReference.loads("myreference/1.0@lasote/testing"),
                               ConanFileReference.loads("br1/1.0@conan/testing")])

    def test_pages(self):
        for number in range(10):
            self._add_build(number)

        # 10 pages, 1 per build
        self.packager.run_builds(1, 10)
        self.runner.assert_tests_for([0])

        # 2 pages, 5 per build
        self.runner.reset()
        self.packager.run_builds(1, 2)
        self.runner.assert_tests_for([0, 2, 4, 6, 8])

        self.runner.reset()
        self.packager.run_builds(2, 2)
        self.runner.assert_tests_for([1, 3, 5, 7, 9])

        # 3 pages, 4 builds in page 1 and 3 in the rest of pages
        self.runner.reset()
        self.packager.run_builds(1, 3)
        self.runner.assert_tests_for([0, 3, 6, 9])

        self.runner.reset()
        self.packager.run_builds(2, 3)
        self.runner.assert_tests_for([1, 4, 7])

        self.runner.reset()
        self.packager.run_builds(3, 3)
        self.runner.assert_tests_for([2, 5, 8])

    def test_deprecation_gcc(self):

        with self.assertRaisesRegexp(Exception, "DEPRECATED GCC MINOR VERSIONS!"):
            ConanMultiPackager("--build missing -r conan.io",
                               "lasote", "mychannel",
                               runner=self.runner,
                               gcc_versions=["4.3", "5.4"],
                               use_docker=True)

    def test_32bits_images(self):
        packager = ConanMultiPackager("--build missing -r conan.io",
                                      "lasote", "mychannel",
                                      runner=self.runner,
                                      use_docker=True,
                                      docker_32_images=True)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertIn("docker pull lasote/conangcc6-i386", self.runner.calls[0])

        self.runner.reset()
        packager = ConanMultiPackager("--build missing -r conan.io",
                                      "lasote", "mychannel",
                                      runner=self.runner,
                                      use_docker=True,
                                      docker_32_images=False)

        packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
        packager.run_builds(1, 1)
        self.assertNotIn("docker pull lasote/conangcc6-i386", self.runner.calls[0])

        self.runner.reset()
        with tools.environment_append({"CONAN_DOCKER_32_IMAGES": "1"}):
            packager = ConanMultiPackager("--build missing -r conan.io",
                                          "lasote", "mychannel",
                                          runner=self.runner,
                                          use_docker=True)

            packager.add({"arch": "x86", "compiler": "gcc", "compiler.version": "6"})
            packager.run_builds(1, 1)
            self.assertIn("docker pull lasote/conangcc6-i386", self.runner.calls[0])

    def test_docker_gcc(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           gcc_versions=["4.3", "5"],
                                           use_docker=True)
        self._add_build(1, "gcc", "4.3")
        self._add_build(2, "gcc", "4.3")
        self._add_build(3, "gcc", "4.3")

        self.packager.run_builds(1, 2)
        self.assertIn("docker pull lasote/conangcc43", self.runner.calls[0])
        self.assertIn('docker run ', self.runner.calls[1])
        self.assertIn('os=os1', self.runner.calls[4])
        self.packager.run_builds(1, 2)
        self.assertIn("docker pull lasote/conangcc43", self.runner.calls[0])

        with tools.environment_append({"CONAN_DOCKER_USE_SUDO": "1"}):
             self.packager.run_builds(1, 2)
             self.assertIn("sudo docker run", self.runner.calls[-1])

        # Next build from 4.3 is cached, not pulls are performed
        self.assertIn('os=os3', self.runner.calls[5])

    def test_docker_clang(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           clang_versions=["3.8", "4.0"],
                                           use_docker=True)

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
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           gcc_versions=["5", "6"],
                                           clang_versions=["3.9", "4.0"],
                                           use_docker=True)

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
        packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel", upload=False)
        self.assertFalse(packager._upload_enabled())

    def test_docker_env_propagated(self):
        # test env
        with tools.environment_append({"CONAN_FAKE_VAR": "32"}):
            self.packager = ConanMultiPackager("--build missing -r conan.io",
                                               "lasote", "mychannel",
                                               runner=self.runner,
                                               gcc_versions=["5", "6"],
                                               clang_versions=["3.9", "4.0"],
                                               use_docker=True)
            self._add_build(1, "gcc", "5")
            self.packager.run_builds(1, 1)
            self.assertIn('-e CONAN_FAKE_VAR=32', self.runner.calls[-1])

    @unittest.skipUnless(sys.platform.startswith("win"), "Requires Windows")
    def test_msvc(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           visual_versions=[15])
        self.packager.add_common_builds()      

        with tools.environment_append({"VisualStudioVersion": "15.0"}):
            self.packager.run_builds(1, 1)
        
        self.assertIn("vcvars", self.runner.calls[1])

    @unittest.skipUnless(sys.platform.startswith("win"), "Requires Windows")
    def test_msvc_no_precommand(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           visual_versions=[15],
                                           exclude_vcvars_precommand=True)
        self.packager.add_common_builds()                                           
        self.packager.run_builds(1, 1)

        self.assertNotIn("vcvars", self.runner.calls[1])

    def test_docker_invalid(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           use_docker=True)

        self._add_build(1, "msvc", "10")

        # Only clang and gcc have docker images
        self.assertRaises(Exception, self.packager.run_builds)

    def test_assign_builds_retrocompatibility(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           gcc_versions=["4.3", "5"],
                                           use_docker=True)
        self.packager.add_common_builds()
        self.packager.builds = [({"os": "Windows"}, {"option": "value"})]
        self.assertEquals(self.packager.items, [BuildConf(settings={'os': 'Windows'},
                                                          options={'option': 'value'},
                                                          env_vars={}, build_requires={},
                                                          reference=None)])

    def test_only_mingw(self):

        mingw_configurations = [("4.9", "x86_64", "seh", "posix")]
        builder = ConanMultiPackager(mingw_configurations=mingw_configurations, visual_versions=[],
                                     username="Pepe", platform_info=platform_mock_for("Windows"),
                                     reference="lib/1.0")
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
        builder = ConanMultiPackager(username="Pepe")
        named_builds = defaultdict(list)
        builder.add_common_builds(shared_option_name="zlib:shared", pure_c=True)
        for settings, options, env_vars, build_requires in builder.builds:
            named_builds[settings['arch']].append([settings, options, env_vars, build_requires])
        builder.named_builds = named_builds

        self.assertEquals(builder.builds, [])
        self.assertEquals(len(builder.named_builds), 2)
        self.assertTrue("x86" in builder.named_builds)
        self.assertTrue("x86_64" in builder.named_builds)

    # Conan remote URLs require the username the be in all lowercase
    def test_url_handling(self):
        runner = MockRunner()
        builder = ConanMultiPackager(username="Pepe",
                                     remotes=["URL1", "URL2"],
                                     upload="URL",
                                     runner=runner)
        builder.add({}, {}, {}, {})
        builder.run_builds()
        print(runner.calls)
        self.assertIn('conan remote add remote0 url2 --insert', runner.calls)
        self.assertIn('conan remote add remote1 url1 --insert', runner.calls)
        self.assertIn('conan remote add upload_repo url', runner.calls)

        runner = MockRunner()
        builder = ConanMultiPackager(username="Pepe",
                                     remotes="URL1, URL2",
                                     upload="URL",
                                     runner=runner)
        builder.add({}, {}, {}, {})
        builder.run_builds()
        self.assertIn('conan remote add remote0 url2 --insert', runner.calls)
        self.assertIn('conan remote add remote1 url1 --insert', runner.calls)
        self.assertIn('conan remote add upload_repo url', runner.calls)

        runner = MockRunner()
        builder = ConanMultiPackager(username="Pepe",
                                     remotes="URL1",
                                     upload="URL",
                                     runner=runner)
        builder.add({}, {}, {}, {})
        builder.run_builds()
        self.assertIn('conan remote add remote0 url1 --insert', runner.calls)
        self.assertIn('conan remote add upload_repo url', runner.calls)

    def test_remotes(self):
        runner = MockRunner()
        builder = ConanMultiPackager(username="Pepe",
                                     remotes=["url1", "url2"],
                                     runner=runner)

        builder.add({}, {}, {}, {})
        builder.run_builds()
        self.assertIn('conan remote add remote0 url2 --insert', runner.calls)
        self.assertIn('conan remote add remote1 url1 --insert', runner.calls)

        runner = MockRunner()
        builder = ConanMultiPackager(username="Pepe",
                                     remotes="myurl1",
                                     runner=runner)

        builder.add({}, {}, {}, {})
        builder.run_builds()
        self.assertIn('conan remote add remote0 myurl1 --insert', runner.calls)

    def test_visual_defaults(self):

        with tools.environment_append({"CONAN_VISUAL_VERSIONS": "10"}):
            builder = ConanMultiPackager(username="Pepe",
                                         platform_info=platform_mock_for("Windows"))
            builder.add_common_builds()
            for settings, _, _, _ in builder.builds:
                self.assertEquals(settings["compiler"], "Visual Studio")
                self.assertEquals(settings["compiler.version"], "10")

        with tools.environment_append({"CONAN_VISUAL_VERSIONS": "10",
                                       "MINGW_CONFIGURATIONS": "4.9@x86_64@seh@posix"}):

            builder = ConanMultiPackager(username="Pepe",
                                         platform_info=platform_mock_for("Windows"))
            builder.add_common_builds()
            for settings, _, _, _ in builder.builds:
                self.assertEquals(settings["compiler"], "gcc")
                self.assertEquals(settings["compiler.version"], "4.9")

    def select_defaults_test(self):
        builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                     gcc_versions=["4.8", "5"],
                                     username="foo")

        self.assertEquals(builder.clang_versions, [])

        with tools.environment_append({"CONAN_GCC_VERSIONS": "4.8, 5"}):
            builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                         username="foo")

            self.assertEquals(builder.clang_versions, [])
            self.assertEquals(builder.gcc_versions, ["4.8", "5"])

        builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                     clang_versions=["4.8", "5"],
                                     username="foo")

        self.assertEquals(builder.gcc_versions, [])

        with tools.environment_append({"CONAN_CLANG_VERSIONS": "4.8, 5"}):
            builder = ConanMultiPackager(platform_info=platform_mock_for("Linux"),
                                         username="foo")

            self.assertEquals(builder.gcc_versions, [])
            self.assertEquals(builder.clang_versions, ["4.8", "5"])

    def test_upload(self):
        runner = MockRunner()
        runner.output = "arepo: myurl"
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     remotes="myurl, otherurl",
                                     platform_info=platform_mock_for("Darwin"))
        builder.add_common_builds()
        builder.run()

        # Duplicated upload remote puts upload repo first (in the remotes order)
        self.assertEqual(runner.calls[0:3], ['conan remote add remote0 otherurl --insert',
                                             'conan remote add upload_repo myurl --insert',
                                             'conan remote list'])

        # Now check that the upload remote order is preserved if we specify it in the remotes
        runner = MockRunner()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     remotes="otherurl, myurl, moreurl",
                                     platform_info=platform_mock_for("Darwin"))
        builder.add_common_builds()
        builder.run()

        # Duplicated upload remote puts upload repo first (in the remotes order)
        self.assertEqual(runner.calls[0:3], ['conan remote add remote0 moreurl --insert',
                                             'conan remote add upload_repo myurl --insert',
                                             'conan remote add remote2 otherurl --insert'])

        self.assertEqual(runner.calls[-1],
                         'conan upload Hello/0.1@pepe/testing --retry 3 --all --force '
                         '--confirm -r=upload_repo')

        runner = MockRunner()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     remotes="otherurl",
                                     platform_info=platform_mock_for("Darwin"))
        builder.add_common_builds()
        builder.run()

        self.assertEqual(runner.calls[0:3],
                         ['conan remote add remote0 otherurl --insert',
                          'conan remote list',
                          'conan remote add upload_repo myurl'])

        self.assertEqual(runner.calls[-1],
                         'conan upload Hello/0.1@pepe/testing --retry 3 --all '
                         '--force --confirm -r=upload_repo')

    def test_login(self):
        runner = MockRunner()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner)

        builder.login("Myremote", "myuser", "mypass", force=False)
        self.assertIn('conan user myuser -p="mypass" -r=Myremote', runner.calls[-1])
        runner.calls = []
        # Already logged, not call conan user again
        builder.login("Myremote", "myuser", "mypass", force=False)
        self.assertEquals(len(runner.calls), 0)
        # Already logged, but forced
        runner.calls = []
        builder.login("Myremote", "myuser", "mypass", force=True)
        self.assertEquals(len(runner.calls), 1)

        # Default users/pass
        runner.calls = []
        builder.login("Myremote2")
        self.assertIn('conan user pepe -p="password" -r=Myremote2', runner.calls[-1])

    def test_check_credentials(self):

        runner = MockRunner()
        runner.output = "arepo: myurl"
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     platform_info=platform_mock_for("Darwin"))
        builder.add_common_builds()
        builder.run()

        # When activated, check credentials before to create the profiles
        self.assertEqual(runner.calls[0], 'conan remote add upload_repo myurl')
        self.assertEqual(runner.calls[2], 'conan user pepe -p="password" -r=upload_repo')
        self.assertIn("conan create", runner.calls[-2])  # Not login again before upload its cached
        self.assertEqual(runner.calls[-1],
                         "conan upload Hello/0.1@pepe/testing --retry 3 --all --force --confirm "
                         "-r=upload_repo")

        runner = MockRunner()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     remotes="otherurl",
                                     platform_info=platform_mock_for("Darwin"))
        builder.add_common_builds()
        builder.run()

        # When upload is not required, credentials verification must be avoided
        self.assertFalse('conan user pepe -p="password" -r=upload_repo' in runner.calls)
        self.assertFalse('conan upload Hello/0.1@pepe/testing --retry 3 '
                         '--all --force --confirm -r=upload_repo' in runner.calls)

        # If we skip the credentials check, the login will be performed just before the upload
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     platform_info=platform_mock_for("Darwin"),
                                     skip_check_credentials=True)
        builder.add_common_builds()
        builder.run()
        self.assertEqual(runner.calls[-2],
                         'conan user pepe -p="password" -r=upload_repo')
        self.assertEqual(runner.calls[-1],
                         "conan upload Hello/0.1@pepe/testing --retry 3 --all --force --confirm "
                         "-r=upload_repo")
