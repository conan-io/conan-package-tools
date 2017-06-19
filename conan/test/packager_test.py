import unittest

from collections import defaultdict

from conan.builds_generator import BuildConf
from conan.packager import ConanMultiPackager
from conans.model.ref import ConanFileReference
from conans.util.files import load
from conans.model.profile import Profile


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
            return read_profile(profile_path, None, None)[0]

    def assert_tests_for(self, numbers):
        """Check if executor has ran the builds that are expected.
        numbers are integers"""
        def assert_profile_for(pr, num):
            assert(pr.settings["compiler"] == 'compiler%d' % num)
            assert(pr.settings["os"] == 'os%d' % num)
            assert(pr.options.as_list() == [('option%d' % num, 'value%d' % num)])

        testp_counter = 0
        for i, call in enumerate(self.calls):
            if call.startswith("conan test_package"):
                profile = self.get_profile_from_trace(i)
                assert_profile_for(profile, numbers[testp_counter])
                testp_counter += 1


class AppTest(unittest.TestCase):

    def setUp(self):
        self.runner = MockRunner()
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner)

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
        profile = self.runner.get_profile_from_trace(1)
        self.assertEquals(profile.settings["os"], "Windows")
        self.assertEquals(profile.settings["compiler"], "gcc")
        self.assertEquals(profile.options.as_list(), [("option1", "One")])
        self.assertEquals(profile.env_values.data[None]["VAR_1"], "ONE")
        self.assertEquals(profile.env_values.data[None]["VAR_2"], "TWO")
        self.assertEquals(profile.build_requires["*"], [ConanFileReference.loads("myreference/1.0@lasote/testing")])

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

    def test_docker_gcc(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           gcc_versions=["4.3", "5.2"],
                                           use_docker=True)
        self._add_build(1, "gcc", "4.3")
        self._add_build(2, "gcc", "4.3")
        self._add_build(3, "gcc", "4.3")

        self.packager.run_builds(1, 2)
        self.assertIn("sudo docker pull lasote/conangcc43", self.runner.calls[1])
        self.assertIn('sudo docker run ', self.runner.calls[2])
        self.assertIn('os=os1', self.runner.calls[5])

        # Next build from 4.3 is cached, not pulls are performed
        self.assertIn('os=os3', self.runner.calls[6])

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
        self.assertIn("sudo docker pull lasote/conanclang38", self.runner.calls[1])
        self.assertIn('sudo docker run ', self.runner.calls[2])
        self.assertIn('os=os1', self.runner.calls[5])

        # Next build from 3.8 is cached, not pulls are performed
        self.assertIn('os=os3', self.runner.calls[6])

    def test_docker_gcc_and_clang(self):
        self.packager = ConanMultiPackager("--build missing -r conan.io",
                                           "lasote", "mychannel",
                                           runner=self.runner,
                                           gcc_versions=["5.4", "6.3"],
                                           clang_versions=["3.9", "4.0"],
                                           use_docker=True)

        self._add_build(1, "gcc", "5.4")
        self._add_build(2, "gcc", "5.4")
        self._add_build(3, "gcc", "5.4")
        self._add_build(4, "clang", "3.9")
        self._add_build(5, "clang", "3.9")
        self._add_build(6, "clang", "3.9")

        self.packager.run_builds(1, 2)
        self.assertIn("sudo docker pull lasote/conangcc54", self.runner.calls[1])
        self.assertIn('sudo docker run ', self.runner.calls[2])
        self.assertIn('os=os1', self.runner.calls[5])
        self.assertIn('os=os3', self.runner.calls[6])

        self.packager.run_builds(2, 2)
        self.assertIn("sudo docker pull lasote/conanclang39", self.runner.calls[18])
        self.assertIn('sudo docker run ', self.runner.calls[19])
        self.assertIn('os=os4', self.runner.calls[22])
        self.assertIn('os=os6', self.runner.calls[23])

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
                                           gcc_versions=["4.3", "5.2"],
                                           use_docker=True)
        self.packager.add_common_builds()
        self.packager.builds = [({"os": "Windows"}, {"option": "value"})]
        self.assertEquals(self.packager.builds, [BuildConf(settings={'os': 'Windows'}, options={'option': 'value'}, env_vars={}, build_requires={})])

    def test_only_mingw(self):

        class PlatformInfoMock(object):
            def system(self):
                return "Windows"

        mingw_configurations = [("4.9", "x86_64", "seh", "posix")]
        builder = ConanMultiPackager(mingw_configurations=mingw_configurations, visual_versions=[], username="Pepe", platform_info=PlatformInfoMock())
        builder.add_common_builds(shared_option_name="zlib:shared", pure_c=True)
        expected = [({'compiler.libcxx': 'libstdc++', 'compiler.exception': 'seh', 'compiler.threads': 'posix', 'compiler.version': '4.9', 'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'mingw_installer:threads': 'posix', 'mingw_installer:arch': 'x86_64', 'mingw_installer:version': '4.9', 'mingw_installer:exception': 'seh'},
                     {},
                     {'*': [ConanFileReference.loads("mingw_installer/0.1@lasote/testing")]}),
                    ({'compiler.exception': 'seh', 'arch': 'x86_64', 'compiler.threads': 'posix', 'compiler.version': '4.9', 'compiler.libcxx': 'libstdc++', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'mingw_installer:threads': 'posix', 'mingw_installer:arch': 'x86_64', 'mingw_installer:version': '4.9', 'mingw_installer:exception': 'seh'},
                     {},
                     {'*': [ConanFileReference.loads("mingw_installer/0.1@lasote/testing")]})]
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

    def test_upload(self):

        class PlatformInfoMock(object):
            def system(self):
                return "Darwin"

        runner = MockRunner()
        runner.output = "arepo: myurl"
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     remotes="myurl, otherurl",
                                     platform_info=PlatformInfoMock())
        builder.add_common_builds()
        builder.run()

        # Duplicated upload remote is ignored
        self.assertEqual(runner.calls[0:5],
                         ['conan remote list',
                          'conan remote remove arepo',
                          'conan remote add upload_repo myurl',
                          'conan remote list',
                          'conan remote add remote0 otherurl --insert'
                          ])
        self.assertEqual(runner.calls[-1],
                         'conan upload Hello/0.1@pepe/testing --retry 3 --all --force -r=upload_repo')

        runner = MockRunner()
        builder = ConanMultiPackager(username="pepe", channel="testing",
                                     reference="Hello/0.1", password="password",
                                     upload="myurl", visual_versions=[], gcc_versions=[],
                                     apple_clang_versions=[],
                                     runner=runner,
                                     remotes="otherurl",
                                     platform_info=PlatformInfoMock())
        builder.add_common_builds()
        builder.run()

        self.assertEqual(runner.calls[0:4],
                         ['conan remote list',
                          'conan remote add upload_repo myurl',
                          'conan remote list',
                          'conan remote add remote0 otherurl --insert'])

        self.assertEqual(runner.calls[-1],
                         'conan upload Hello/0.1@pepe/testing --retry 3 --all --force -r=upload_repo')