import unittest

from conan.builds_generator import get_visual_builds, get_mingw_builds, get_osx_apple_clang_builds, get_linux_gcc_builds, get_linux_clang_builds
from conans.model.ref import ConanFileReference


class GeneratorsTest(unittest.TestCase):

    def test_mingw_generator(self):

        mingw_configurations = [("4.9", "x86", "dwarf2", "posix")]

        builds = get_mingw_builds(mingw_configurations, ConanFileReference.loads("mingw_installer/1.0@lasote/testing"), ["x86"])
        expected = [
            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': 'libstdc++',
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {'mingw_installer:arch': 'x86', 'mingw_installer:version': '4.9',
              'mingw_installer:threads': 'posix', 'mingw_installer:exception': 'dwarf2'},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@lasote/testing")]}),

            ({'compiler.version': '4.9', 'compiler.libcxx': 'libstdc++', 'compiler': 'gcc',
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {'mingw_installer:arch': 'x86', 'mingw_installer:version': '4.9',
              'mingw_installer:threads': 'posix', 'mingw_installer:exception': 'dwarf2'},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@lasote/testing")]})]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_osx_apple_clang_builds(self):
        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], "pack:shared", pure_c=False)
        expected = [({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}),
                   ]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], "pack:shared", pure_c=True)
        expected = [({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}),
                    ]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_linux_gcc_builds(self):
        builds = get_linux_gcc_builds(["6.0"], ["x86_64"], "pack:shared", pure_c=False)
        expected = [({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {})]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(["6.0"], ["x86_64"], "pack:shared", pure_c=True)
        expected = [({'arch': 'x86_64', 'compiler.version': '6.0', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.version': '6.0', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.version': '6.0', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.version': '6.0', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {})]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_linux_clang_builds(self):
        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=False)
        expected = [({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {})]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=True)
        expected = [({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {})]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_visual_build_generator(self):
        builds = get_visual_builds(visual_versions=["10", "14"], archs=["x86"], visual_runtimes=["MDd", "MTd"],
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True)

        expected = [
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MTd'}, {}, {}, {}),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MDd'}, {}, {}, {}),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MTd'}, {}, {}, {}),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {}, {}, {})]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"], visual_runtimes=["MDd"],
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True)

        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': True}, {}, {})]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"], visual_runtimes=["MDd"],
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False)
        expected = [
        ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
          {'libpng:shared': False}, {}, {}),
        ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
          {'libpng:shared': True}, {}, {})]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"], visual_runtimes=["MTd"],
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False)
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MTd', 'compiler.version': '10', 'arch': 'x86', 'build_type': 'Debug'},
             {'libpng:shared': False}, {}, {})]

        self.assertEquals([tuple(a) for a in builds], expected)
