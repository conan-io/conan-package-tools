import unittest

from conans import tools

from cpt.builds_generator import get_visual_builds, get_mingw_builds, get_osx_apple_clang_builds, get_linux_gcc_builds, get_linux_clang_builds
from conans.model.ref import ConanFileReference


class GeneratorsTest(unittest.TestCase):

    def test_mingw_generator(self):

        mingw_configurations = [("4.9", "x86", "dwarf2", "posix")]
        ref = ConanFileReference.loads("lib/1.0@conan/stable")
        builds = get_mingw_builds(mingw_configurations,
                                  ConanFileReference.loads("mingw_installer/1.0@conan/stable"),
                                  ["x86"], "pack:shared", ["Release", "Debug"], options={},
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

        builds = get_mingw_builds(mingw_configurations, ConanFileReference.loads(
            "mingw_installer/1.0@conan/stable"), ["x86"], "pack:shared", ["Release"], options={})
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

        builds = get_mingw_builds(mingw_configurations, ConanFileReference.loads(
            "mingw_installer/1.0@conan/stable"), ["x86"], "pack:shared", ["Debug"], options={})
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

        builds = get_mingw_builds(mingw_configurations,
                                  ConanFileReference.loads("mingw_installer/1.0@conan/stable"),
                                  ["x86"], "pack:shared", ["Release", "Debug"], options={"pack:foobar": True, "foobar:qux": "data"},
                                  reference=ref)
        expected = [
            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': "libstdc++",
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {'pack:shared': True, "pack:foobar": True, "foobar:qux": "data"},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref),
            ({'compiler.version': '4.9', 'compiler': 'gcc', 'compiler.libcxx': "libstdc++",
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {'pack:shared': True, "pack:foobar": True, "foobar:qux": "data"},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref),

            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': "libstdc++",
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {'pack:shared': False, "pack:foobar": True, "foobar:qux": "data"},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref),
            ({'compiler.version': '4.9', 'compiler': 'gcc', 'compiler.libcxx': "libstdc++",
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {'pack:shared': False, "pack:foobar": True, "foobar:qux": "data"},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_mingw_builds(mingw_configurations,
                                  ConanFileReference.loads("mingw_installer/1.0@conan/stable"),
                                  ["x86"], None, ["Release", "Debug"],
                                  options={"pack:foobar": True, "foobar:qux": "data"},
                                  reference=ref)
        expected = [
            ({'build_type': 'Release', 'compiler.version': '4.9', 'compiler.libcxx': "libstdc++",
              'compiler': 'gcc', 'arch': 'x86', 'compiler.exception': 'dwarf2',
              'compiler.threads': 'posix'},
             {"pack:foobar": True, "foobar:qux": "data"},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref),
            ({'compiler.version': '4.9', 'compiler': 'gcc', 'compiler.libcxx': "libstdc++",
              'build_type': 'Debug', 'compiler.exception': 'dwarf2', 'compiler.threads': 'posix',
              'arch': 'x86'},
             {"pack:foobar": True, "foobar:qux": "data"},
             {},
             {'*': [ConanFileReference.loads("mingw_installer/1.0@conan/stable")]}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_osx_apple_clang_builds(self):
        ref = ConanFileReference.loads("lib/1.0@conan/stable")
        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], "pack:shared", pure_c=False, build_types=["Debug", "Release"], options={}, reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang', 'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], "pack:shared", pure_c=True, build_types=["Debug", "Release"], options={})
        expected = [({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], "pack:shared", pure_c=False, build_types=["Debug"], options={})
        expected = [({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], "pack:shared", pure_c=True, build_types=["Release"], options={})
        expected = [({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], "pack:shared", pure_c=False,
                                            build_types=["Debug", "Release"], options={"qux:foobar": False, "foo:pkg": "bar"}, reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': True, "qux:foobar": False, "foo:pkg": "bar"}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': True, "qux:foobar": False, "foo:pkg": "bar"}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {'pack:shared': False, "qux:foobar": False, "foo:pkg": "bar"}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {'pack:shared': False, "qux:foobar": False, "foo:pkg": "bar"}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_osx_apple_clang_builds(["8.0"], ["x86_64"], None, pure_c=False,
                                            build_types=["Debug", "Release"],
                                            options={"qux:foobar": False, "foo:pkg": "bar"}, reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Debug'},
                     {"qux:foobar": False, "foo:pkg": "bar"}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.libcxx': 'libc++', 'compiler': 'apple-clang',
                      'compiler.version': '8.0', 'build_type': 'Release'},
                     {"qux:foobar": False, "foo:pkg": "bar"}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_linux_gcc_builds(self):
        builds = get_linux_gcc_builds(["6"], ["x86_64"], "pack:shared", pure_c=False, build_types=["Debug", "Release"], options={})
        expected = [({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11', 'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(["6"], ["x86_64"], "pack:shared", pure_c=True, build_types=["Debug", "Release"], options={})
        expected = [({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(["6"], ["x86_64"], "pack:shared", pure_c=False, build_types=["Debug"], options={})
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

        builds = get_linux_gcc_builds(["6"], ["x86_64"], "pack:shared", pure_c=True, build_types=["Debug"], options={})
        expected = [({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(["6"], ["x86_64"], "pack:shared", pure_c=False, build_types=["Release"], options={})
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

        builds = get_linux_gcc_builds(["6"], ["x86_64"], "pack:shared", pure_c=True, build_types=["Release"], options={})
        expected = [({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(["6"], ["x86_64"], "pack:shared", pure_c=False, build_types=["Debug", "Release"],
                                      options={"foo:bar": "qux", "pkg:qux": False})
        expected = [({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6',
                      'arch': 'x86_64'},
                     {'pack:shared': True, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': True, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '6',
                      'arch': 'x86_64'},
                     {'pack:shared': False, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None),
                    ({'compiler': 'gcc', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++11',
                      'compiler.version': '6', 'arch': 'x86_64'},
                     {'pack:shared': False, "foo:bar": "qux", "pkg:qux": False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_gcc_builds(["6"], ["x86_64"], None, pure_c=True, build_types=["Debug", "Release"],
                                      options={"qux:bar": "foo", "*:pkg": False})
        expected = [({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Debug', 'compiler': 'gcc'},
                     {"qux:bar": "foo", "*:pkg": False}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '6', 'build_type': 'Release', 'compiler': 'gcc'},
                     {"qux:bar": "foo", "*:pkg": False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_get_linux_clang_builds(self):
        self.maxDiff = None
        ref = ConanFileReference.loads("lib/2.3@conan/stable")
        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=False,
                                        build_types=["Debug", "Release"], options={},
                                        reference=ref)
        expected = [({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libstdc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Release', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False}, {}, {}, ref)]
        b = [tuple(a) for a in builds]
        self.assertEquals(b, expected)

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=True,
                                        build_types=["Debug", "Release"], options={}, reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=False,
                                        build_types=["Debug"], options={}, reference=ref)
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

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=True,
                                        build_types=["Debug"], options={}, reference=ref)
        expected = [({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, ref),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Debug', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=False, build_types=["Release"], options={}, reference=ref)
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

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=True, build_types=["Release"], options={}, reference=None)
        expected = [({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': True}, {}, {}, None),
                    ({'arch': 'x86_64', 'compiler.version': '4.0', 'build_type': 'Release', 'compiler': 'clang'},
                     {'pack:shared': False}, {}, {}, None)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], "pack:shared", pure_c=False,
                                        build_types=["Debug"], options={"foo:bar": "qux", "pkg:shared": True}, reference=ref)
        expected = [({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': True, "foo:bar": "qux", "pkg:shared": True}, {}, {}, ref),
                    (
                    {'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0',
                     'arch': 'x86_64'},
                    {'pack:shared': True, "foo:bar": "qux", "pkg:shared": True}, {}, {}, ref),
                    ({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '4.0', 'arch': 'x86_64'},
                     {'pack:shared': False, "foo:bar": "qux", "pkg:shared": True}, {}, {}, ref),
                    (
                    {'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++', 'compiler.version': '4.0',
                     'arch': 'x86_64'},
                    {'pack:shared': False, "foo:bar": "qux", "pkg:shared": True}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_linux_clang_builds(["4.0"], ["x86_64"], None, pure_c=False,
                                        build_types=["Debug"], options={"foo:bar": "qux", "pkg:shared": True},
                                        reference=ref)
        expected = [({'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libstdc++',
                      'compiler.version': '4.0', 'arch': 'x86_64'},
                     {"foo:bar": "qux", "pkg:shared": True}, {}, {}, ref),
                    (
                        {'compiler': 'clang', 'build_type': 'Debug', 'compiler.libcxx': 'libc++',
                         'compiler.version': '4.0',
                         'arch': 'x86_64'},
                        {"foo:bar": "qux", "pkg:shared": True}, {}, {}, ref)]
        self.assertEquals([tuple(a) for a in builds], expected)

    def test_visual_build_generator(self):
        ref = ConanFileReference.loads("lib/1.0@conan/stable")
        builds = get_visual_builds(visual_versions=["10", "14"],
                                   archs=["x86"], visual_runtimes=["MDd", "MTd"],
                                   visual_toolsets=None,
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={},
                                   reference=ref)

        expected = [
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MDd'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MTd'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MTd'}, {}, {}, {}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"], visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={})

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

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={})
        expected = [
        ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
          {'libpng:shared': False}, {}, {}, None),
        ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10'},
          {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MTd"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MTd', 'compiler.version': '10', 'arch': 'x86', 'build_type': 'Debug'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10", "14"], archs=["x86"],
                                   visual_runtimes=["MDd", "MTd"],
                                   visual_toolsets=None,
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug"],
                                   options={})

        expected = [
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MDd'}, {}, {}, {}, None),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MTd'}, {}, {}, {}, None),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MDd'}, {}, {}, {}, None),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MTd'}, {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug"],
                                   options={})

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

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug"],
                                   options={})
        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MTd"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug"],
                                   options={})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MTd', 'compiler.version': '10', 'arch': 'x86',
              'build_type': 'Debug'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        #############

        builds = get_visual_builds(visual_versions=["10", "14"], archs=["x86_64"],
                                   visual_runtimes=["MD", "MT"],
                                   visual_toolsets=None,
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Release"],
                                   options={})

        expected = [
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MD'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MT'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MD'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MT'}, {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Release"],
                                   options={})

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

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Release"],
                                   options={})
        expected = [
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MT"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Release"],
                                   options={})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MT', 'compiler.version': '10', 'arch': 'x86',
              'build_type': 'Release'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        #############

        builds = get_visual_builds(visual_versions=["10", "14"], archs=["x86_64"],
                                   visual_runtimes=["MD", "MT"],
                                   visual_toolsets=None,
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["RelWithDebInfo"],
                                   options={})

        expected = [
            ({'arch': 'x86_64', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MD'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MT'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MD'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MT'}, {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["RelWithDebInfo"],
                                   options={})

        expected = [
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86_64', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86_64', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"],
                                   visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["RelWithDebInfo"],
                                   options={})
        expected = [
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MT"], visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["RelWithDebInfo"],
                                   options={})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MT', 'compiler.version': '10', 'arch': 'x86',
              'build_type': 'RelWithDebInfo'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        #############

        builds = get_visual_builds(visual_versions=["10", "14"], archs=["x86_64"],
                                   visual_runtimes=["MD", "MT"], visual_toolsets=None,
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["MinSizeRel"],
                                   options={})

        expected = [
            ({'arch': 'x86_64', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MD'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MT'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MD'}, {}, {}, {}, None),
            ({'arch': 'x86_64', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MT'}, {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"], visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["MinSizeRel"],
                                   options={})

        expected = [
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86_64', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86_64', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MD"], visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["MinSizeRel"],
                                   options={})
        expected = [
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False}, {}, {}, None),
            ({'compiler.runtime': 'MD', 'arch': 'x86', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MT"], visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=False,
                                   build_types=["MinSizeRel"],
                                   options={})
        expected = [
            ({'compiler': 'Visual Studio', 'compiler.runtime': 'MT', 'compiler.version': '10', 'arch': 'x86',
              'build_type': 'MinSizeRel'},
             {'libpng:shared': False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        #############

        builds = get_visual_builds(visual_versions=["10", "14"], archs=["x86"],
                                   visual_runtimes=["MD", "MDd"], visual_toolsets=None,
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={},
                                   reference=ref)

        expected = [
        ({'arch': 'x86', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MD'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MD'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MD'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10', 'compiler.runtime': 'MDd'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'MinSizeRel', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MD'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'RelWithDebInfo', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MD'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Release', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MD'}, {}, {}, {}, ref),
        ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14', 'compiler.runtime': 'MDd'}, {}, {}, {}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)

        #############

        builds = get_visual_builds(visual_versions=["10", "14"], archs=["x86"],
                                   visual_runtimes=["MDd", "MTd"], visual_toolsets=None,
                                   shared_option_name=None,
                                   dll_with_static_runtime=False,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={"msvc:sdk": 10, "pkg:shared": True},
                                   reference=ref)

        expected = [
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MDd'}, {"msvc:sdk": 10, "pkg:shared": True}, {}, {}, ref),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '10',
              'compiler.runtime': 'MTd'}, {"msvc:sdk": 10, "pkg:shared": True}, {}, {}, ref),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MDd'}, {"msvc:sdk": 10, "pkg:shared": True}, {}, {}, ref),
            ({'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio', 'compiler.version': '14',
              'compiler.runtime': 'MTd'}, {"msvc:sdk": 10, "pkg:shared": True}, {}, {}, ref)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"], visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=True,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={"pkg:shared": False, "pkg:foo": "bar"})

        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False, "pkg:shared": False, "pkg:foo": "bar"}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True, "pkg:shared": False, "pkg:foo": "bar"}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False, "pkg:shared": False, "pkg:foo": "bar"}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86_64', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True, "pkg:shared": False, "pkg:foo": "bar"}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        builds = get_visual_builds(visual_versions=["10"], archs=["x86", "x86_64"],
                                   visual_runtimes=["MDd"], visual_toolsets=None,
                                   shared_option_name="libpng:shared",
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={"pkg:shared": False, "pkg:fPIC": False})
        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': False, "pkg:shared": False, "pkg:fPIC": False}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '10'},
             {'libpng:shared': True, "pkg:shared": False, "pkg:fPIC": False}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

    def test_visual_toolsets(self):

        builds = get_visual_builds(visual_versions=["15"], archs=["x86"],
                                   visual_runtimes=["MDd"], visual_toolsets={"15": ["v140",
                                                                                    "v140_xp"]},
                                   shared_option_name=None,
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={})
        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '15', 'compiler.toolset': 'v140'},
             {}, {}, {}, None),
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '15', 'compiler.toolset': 'v140_xp'},
             {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)

        # Same with environment passing None in the parameter
        with tools.environment_append({"CONAN_VISUAL_TOOLSETS": "15=v140;v140_xp,11=v140;v140_xp"}):
            builds = get_visual_builds(visual_versions=["15"], archs=["x86"],
                                       visual_runtimes=["MDd"], visual_toolsets=None,
                                       shared_option_name=None,
                                       dll_with_static_runtime=True,
                                       vs10_x86_64_enabled=False,
                                       build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                       options={})
            self.assertEquals([tuple(a) for a in builds], expected)

        # Invalid mapping generates builds without toolsets (visual 10 != visual 15)
        builds = get_visual_builds(visual_versions=["15"], archs=["x86"],
                                   visual_runtimes=["MDd"], visual_toolsets={"10": ["v140",
                                                                                    "v140_xp"]},
                                   shared_option_name=None,
                                   dll_with_static_runtime=True,
                                   vs10_x86_64_enabled=False,
                                   build_types=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
                                   options={})
        expected = [
            ({'compiler.runtime': 'MDd', 'arch': 'x86', 'build_type': 'Debug', 'compiler': 'Visual Studio',
              'compiler.version': '15'},
             {}, {}, {}, None)]

        self.assertEquals([tuple(a) for a in builds], expected)
