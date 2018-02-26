import unittest

from conan.builds_generator import get_visual_builds, get_mingw_builds, get_osx_apple_clang_builds, get_linux_gcc_builds, get_linux_clang_builds, _combine_common_options, _option_dict_from_combination
from conans.model.ref import ConanFileReference


class GeneratorsTest(unittest.TestCase):

    def test_mingw_generator(self):

        mingw_configurations = [("4.9", "x86", "dwarf2", "posix")]
        ref = ConanFileReference.loads("lib/1.0@conan/stable")
        builds = get_mingw_builds(mingw_configurations=mingw_configurations,
                                  mingw_installer_reference=ConanFileReference.loads("mingw_installer/1.0@conan/stable"),
                                  archs=["x86"],
                                  build_types=["Release", "Debug"],
                                  common_options={"pack:shared":[True, False]},
                                  reference=ref)
        expected = [
            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': "libstdc++",
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {'pack:shared': True},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref),
            ({'compiler.version': '4.9', 'compiler': 'gcc', 'compiler.libcxx': "libstdc++",
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {'pack:shared': True},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref),

            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': "libstdc++",
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {'pack:shared': False},
                {},
                {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref),
            ({'compiler.version': '4.9', 'compiler': 'gcc', 'compiler.libcxx': "libstdc++",
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {'pack:shared': False},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_mingw_builds(mingw_configurations=mingw_configurations,
                                  mingw_installer_reference=ConanFileReference.loads("mingw_installer/1.0@conan/stable"),
                                  archs=["x86"],
                                  build_types=["Release"],
                                  common_options={"pack:shared":[True, False]})
        expected = [
            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': "libstdc++",
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {'pack:shared': True},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, None),
            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': "libstdc++",
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {'pack:shared': False},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_mingw_builds(mingw_configurations=mingw_configurations,
                                  mingw_installer_reference=ConanFileReference.loads("mingw_installer/1.0@conan/stable"),
                                  archs=["x86"],
                                  build_types=["Debug"],
                                  common_options={"pack:shared":[True, False]})
        expected = [
            ({'compiler.version': '4.9', 'compiler': 'gcc', 'compiler.libcxx': "libstdc++",
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {'pack:shared': True},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, None),
            ({'compiler.version': '4.9', 'compiler': 'gcc', 'compiler.libcxx': "libstdc++",
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {'pack:shared': False},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_osx_apple_clang_builds(self):
        ref = ConanFileReference.loads("lib/1.0@conan/stable")
        builds = get_osx_apple_clang_builds(apple_clang_versions=["8.0"],
                                            archs=["x86_64"],
                                            pure_c=False,
                                            build_types=["Debug", "Release"],
                                            common_options={"pack:shared":[True, False]},
                                            reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(apple_clang_versions=["8.0"],
                                            archs=["x86_64"],
                                            pure_c=True,
                                            build_types=["Debug", "Release"],
                                            common_options={"pack:shared": [True, False]})
        expected = [({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(apple_clang_versions=["8.0"],
                                            archs=["x86_64"],
                                            pure_c=False,
                                            build_types=["Debug"],
                                            common_options={"pack:shared": [True, False]})
        expected = [({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(apple_clang_versions=["8.0"],
                                            archs=["x86_64"],
                                            pure_c=True,
                                            build_types=["Release"],
                                            common_options={"pack:shared":[True, False]})
        expected = [({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_linux_gcc_builds(self):
        builds = get_linux_gcc_builds(gcc_versions=["6"],
                                      archs=["x86_64"],
                                      pure_c=False,
                                      build_types=["Debug", "Release"],
                                      common_options={"pack:shared": [True, False]})
        expected = [({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(gcc_versions=["6"],
                                      archs=["x86_64"],
                                      pure_c=True,
                                      build_types=["Debug", "Release"],
                                      common_options={"pack:shared":[True, False]})
        expected = [({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(gcc_versions=["6"],
                                      archs=["x86_64"],
                                      pure_c=False,
                                      build_types=["Debug"],
                                      common_options={"pack:shared":[True, False]})
        expected = [({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(gcc_versions=["6"],
                                      archs=["x86_64"],
                                      pure_c=True,
                                      build_types=["Debug"],
                                      common_options={"pack:shared":[True, False]})
        expected = [({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(gcc_versions=["6"],
                                      archs=["x86_64"],
                                      pure_c=False,
                                      build_types=["Release"],
                                      common_options={"pack:shared":[True, False]})
        expected = [({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(gcc_versions=["6"],
                                      archs=["x86_64"],
                                      pure_c=True,
                                      build_types=["Release"],
                                      common_options={"pack:shared":[True, False]})
        expected = [({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_linux_clang_builds(self):
        self.maxDiff = None
        ref = ConanFileReference.loads("lib/2.3@conan/stable")
        builds = get_linux_clang_builds(clang_versions=["4.0"],
                                        archs=["x86_64"],
                                        pure_c=False,
                                        build_types=["Debug", "Release"],
                                        common_options={"pack:shared":[True, False]},
                                        reference=ref)
        expected = [({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libstdc++'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug','compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libc++'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libstdc++'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libc++'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libstdc++'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libc++'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libstdc++'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'clang', 'compiler.version': '4.0', 'compiler.libcxx': 'libc++'},
                     {'pack:shared': False}, {}, {}, ref)]
        b = [tuple(a) for a in builds]
        self.assertEquals(b, expected)

        builds = get_linux_clang_builds(clang_versions=["4.0"],
                                        archs=["x86_64"],
                                        pure_c=True,
                                        build_types=["Debug", "Release"],
                                        common_options={"pack:shared":[True, False]},
                                        reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(clang_versions=["4.0"],
                                        archs=["x86_64"],
                                        pure_c=False,
                                        build_types=["Debug"],
                                        common_options={"pack:shared":[True, False]},
                                        reference=ref)
        expected = [({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0',
                     'arch': 'x86_64'},
                    {'pack:shared': True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0',
                     'arch': 'x86_64'},
                    {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(clang_versions=["4.0"],
                                        archs=["x86_64"],
                                        pure_c=True,
                                        build_types=["Debug"],
                                        common_options={"pack:shared":[True, False]},
                                        reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(clang_versions=["4.0"],
                                        archs=["x86_64"],
                                        pure_c=False,
                                        build_types=["Release"],
                                        common_options={"pack:shared":[True, False]},
                                        reference=ref)
        expected = [({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, ref),
                    (
                    {'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0',
                     'arch': 'x86_64'},
                    {'pack:shared': True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, ref),
                    (
                    {'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0',
                     'arch': 'x86_64'},
                    {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(clang_versions=["4.0"],
                                        archs=["x86_64"],
                                        pure_c=True,
                                        build_types=["Release"],
                                        common_options={"pack:shared":[True, False]},
                                        reference=None)
        expected = [({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_visual_build_generator(self):
        ref = ConanFileReference.loads("lib/1.0@conan/stable")
        builds = get_visual_builds(visual_versions=["10", "14"],
                                   archs=["x86"],
                                   visual_runtimes=["MDd", "MTd"],
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug", "Release"],
                                   common_options={},
                                   reference=ref)

        expected = [
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MTd'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MDd'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MTd'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {}, {}, {}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"],
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug", "Release"],
                                   common_options={"libpng:shared": [True, False]})

        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"],
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug", "Release"],
                                   common_options={"libpng:shared": [True, False]})
        expected = [
        ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
          {'libpng:shared': False}, {}, {}, None),
        ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
          {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MTd"],
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug", "Release"],
                                   common_options={"libpng:shared": [True, False]})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MTd', 'compiler.version': '10', 'arch': 'x86', 'build_type': 'Debug'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10", "14"],
                                   archs=["x86"],
                                   visual_runtimes=["MDd", "MTd"],
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug"],
                                   common_options={})

        expected = [
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MTd'}, {}, {}, {}, None),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MDd'}, {}, {}, {}, None),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MTd'}, {}, {}, {}, None),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MDd'}, {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"],
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug"],
                                   common_options={"libpng:shared": [True, False]})

        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"],
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug"],
                                   common_options={"libpng:shared": [True, False]})
        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MTd"],
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug"],
                                   common_options={"libpng:shared": [True, False]})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MTd', 'compiler.version': '10', 'arch': 'x86',
              'build_type': 'Debug'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        #############

        builds = get_visual_builds(visual_versions=["10", "14"],
                                   archs=["x86_64"],
                                   visual_runtimes=["MD", "MT"],
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Release"],
                                   common_options={})

        expected = [
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MT'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MD'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MT'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MD'}, {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"],
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Release"],
                                   common_options={"libpng:shared": [True, False]})

        expected = [
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"],
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Release"],
                                   common_options={"libpng:shared": [True, False]})
        expected = [
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"],
                                   archs=["x86", "x86_64"],
                                   visual_runtimes=["MT"],
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Release"],
                                   common_options={"libpng:shared": [True, False]})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MT', 'compiler.version': '10', 'arch': 'x86',
              'build_type': 'Release'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

    def options_test(self):
        options = {"shared": [True, False], "opt": [True, False]}
        combinations = _combine_common_options(options)
        self.assertEquals(combinations, [(("shared", True), ("opt", True)),
                                         (("shared", True), ("opt", False)),
                                         (("shared", False), ("opt", True)),
                                         (("shared", False), ("opt", False))])

        options = {"shared": [True, False]}
        combinations = _combine_common_options(options)
        self.assertEquals(combinations, [(("shared", True)), (("shared", False))])


        expanded_option1 = (("shared", True), ("opt", True))
        option_dict = _option_dict_from_combination(expanded_option1)
        self.assertEqual(option_dict, {"shared": True, "opt": True})

        expanded_option2 = (("shared", True), ("opt", False))
        option_dict = _option_dict_from_combination(expanded_option2)
        self.assertEqual(option_dict, {"shared": True, "opt": False})

        single_expanded_option = (("shared", True))
        option_dict = _option_dict_from_combination(single_expanded_option)
        self.assertEqual(option_dict, {"shared": True})

    def functional_options_test(self):
        ref = ConanFileReference.loads("lib/1.0@conan/stable")
        builds = get_visual_builds(visual_versions=["14"],
                                   archs=["x86"],
                                   visual_runtimes=["MDd"],
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug"],
                                   common_options={"opt1":[True, False], "opt2":["value1", "value2"]},
                                   reference=ref)

        expected = [
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {"opt1":True, "opt2":"value1"}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {"opt1":True, "opt2":"value2"}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {"opt1":False, "opt2":"value1"}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {"opt1":False, "opt2":"value2"}, {}, {}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)


        ref = ConanFileReference.loads("lib/2.3@conan/stable")
        builds = get_linux_clang_builds(clang_versions=["4.0"],
                                        archs=["x86_64"],
                                        pure_c=True,
                                        build_types=["Debug"],
                                        common_options={"pack:shared":[True, False], "my_option":[True, False, "other"]},
                                        reference=ref)
        expected = [({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0'},
                     {'pack:shared': True, "my_option":True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug','compiler': 'clang', 'compiler.version': '4.0'},
                     {'pack:shared': True, "my_option":False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0'},
                     {'pack:shared': True, "my_option":"other"}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0'},
                     {'pack:shared': False, "my_option":True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0'},
                     {'pack:shared': False, "my_option":False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'clang', 'compiler.version': '4.0'},
                     {'pack:shared': False, "my_option":"other"}, {}, {}, ref)]
        b = [tuple(a) for a in builds]
        self.assertEquals(b, expected)