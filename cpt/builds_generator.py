import copy
import os
from collections import namedtuple

from conans.model.ref import ConanFileReference
from conans.model.version import Version
from cpt.tools import split_colon_env, transform_list_options_to_dict

default_gcc_versions = ["4.9", "5", "6", "7", "8"]
default_clang_versions = ["3.8", "3.9", "4.0", "5.0", "6.0", "7.0"]
default_visual_versions = ["14", "15"]
default_visual_runtimes = ["MT", "MD", "MTd", "MDd"]
default_apple_clang_versions = ["9.0", "9.1", "10.0"]
default_archs = ["x86", "x86_64"]
default_build_types = ["Release", "Debug"]


def get_mingw_package_reference():
    env_ref = os.getenv("CONAN_MINGW_INSTALLER_REFERENCE")
    return ConanFileReference.loads(env_ref or"mingw_installer/1.0@conan/stable")


def get_mingw_config_from_env():
    tmp = os.getenv("MINGW_CONFIGURATIONS", "")
    # 4.9@x86_64@seh@posix",4.9@x86_64@seh@win32"
    if not tmp:
        return []
    ret = []
    confs = tmp.split(",")
    for conf in confs:
        conf = conf.strip()
        ret.append(conf.split("@"))
    return ret


def get_env_visual_toolsets():
    ret = {}
    var = split_colon_env("CONAN_VISUAL_TOOLSETS")
    if not var:
        return None
    for toolset_versions in var:
        tmp = toolset_versions.split("=")
        if len(tmp) != 2:
            raise Exception("Invalid value for CONAN_VISUAL_TOOLSETS env variable, use "
                            "'14=v140;v140_xp,12=v120_xp'")
        visual_version, tmp_toolsets = tmp
        toolsets = tmp_toolsets.split(";")
        ret[visual_version] = toolsets
    return ret


class BuildGenerator(object):

    def __init__(self, reference, os_name, gcc_versions, apple_clang_versions, clang_versions,
                 visual_versions, visual_runtimes, visual_toolsets, vs10_x86_64_enabled,
                 mingw_configurations, archs, allow_gcc_minors,  build_types, options):

        self._visual_toolsets = visual_toolsets
        self._os_name = os_name
        self._reference = reference
        self._vs10_x86_64_enabled = vs10_x86_64_enabled
        self._allow_gcc_minors = allow_gcc_minors or os.getenv("CONAN_ALLOW_GCC_MINORS", False)

        self._clang_versions = clang_versions or split_colon_env("CONAN_CLANG_VERSIONS")
        self._gcc_versions = gcc_versions or split_colon_env("CONAN_GCC_VERSIONS")

        # If there are some GCC versions declared then we don't default the clang
        # versions
        if self._clang_versions is None:
            if not self._gcc_versions:
                self._clang_versions = default_clang_versions
            else:
                self._clang_versions = []

        # If there are some CLANG versions declared then we don't default the gcc
        # versions
        if self._gcc_versions is None:
            if self._clang_versions == default_clang_versions:
                self._gcc_versions = default_gcc_versions
            else:
                self._gcc_versions = []

        if self._gcc_versions and not self._allow_gcc_minors:
            for a_version in self._gcc_versions:
                if Version(str(a_version)) >= Version("5") and "." in str(a_version):
                    raise Exception("""
******************* DEPRECATED GCC MINOR VERSIONS! ***************************************

- The use of gcc versions >= 5 and specifying the minor version (e.j "5.4") is deprecated.
- The ABI of gcc >= 5 (5, 6, and 7) is compatible between minor versions (e.j 5.3 is compatible with 5.4)
- Specify only the major in your script:
   - CONAN_GCC_VERSIONS="5,6,7" if you are using environment variables.
   - gcc_versions=["5", "6", "7"] if you are using the constructor parameter.

You can still keep using the same docker images, or use the new "conanio/gcc5", "conanio/gcc6", "conanio/gcc7"

If you still want to keep the old behavior, set the environment var CONAN_ALLOW_GCC_MINORS or pass the
"allow_gcc_minors=True" parameter. But it is not recommended, if your packages are public most users
won't be able to use them.

******************************************************************************************

""")

        self._visual_versions = visual_versions or split_colon_env("CONAN_VISUAL_VERSIONS")
        if self._visual_versions is None:
            if not mingw_configurations and not get_mingw_config_from_env():
                self._visual_versions = default_visual_versions
            else:
                self._visual_versions = []
        elif mingw_configurations or get_mingw_config_from_env():
            self._visual_versions = []

        self._visual_runtimes = visual_runtimes or split_colon_env("CONAN_VISUAL_RUNTIMES")
        if self._visual_runtimes is None:
            self._visual_runtimes = default_visual_runtimes

        self._apple_clang_versions = apple_clang_versions or split_colon_env("CONAN_APPLE_CLANG_VERSIONS")

        if self._apple_clang_versions is None:
            self._apple_clang_versions = default_apple_clang_versions

        self._mingw_configurations = mingw_configurations or get_mingw_config_from_env()

        _default_archs = ["x86_64"] if self._os_name == "Darwin" else default_archs

        self._archs = archs or split_colon_env("CONAN_ARCHS")
        if self._archs is None:
            self._archs = _default_archs

        self._build_types = build_types or split_colon_env("CONAN_BUILD_TYPES")
        if self._build_types is None:
            self._build_types = default_build_types

        options = options or split_colon_env("CONAN_OPTIONS")
        if options is None:
            options = []
        self._options = transform_list_options_to_dict(options)

    def get_builds(self, pure_c, shared_option_name, dll_with_static_runtime, reference=None):

        ref = reference or self._reference

        if self._os_name == "Windows":
            if self._mingw_configurations:
                builds = get_mingw_builds(self._mingw_configurations,
                                          get_mingw_package_reference(), self._archs,
                                          shared_option_name, self._build_types, self._options, ref)
            else:
                builds = []
            builds.extend(get_visual_builds(self._visual_versions, self._archs,
                                            self._visual_runtimes, self._visual_toolsets,
                                            shared_option_name, dll_with_static_runtime,
                                            self._vs10_x86_64_enabled,
                                            self._build_types, self._options, ref))
            return builds
        elif self._os_name == "Linux":
            builds = get_linux_gcc_builds(self._gcc_versions, self._archs, shared_option_name,
                                          pure_c, self._build_types, self._options, ref)
            builds.extend(get_linux_clang_builds(self._clang_versions, self._archs,
                                                 shared_option_name, pure_c, self._build_types,
                                                 self._options, ref))
            return builds
        elif self._os_name == "Darwin":
            return get_osx_apple_clang_builds(self._apple_clang_versions, self._archs,
                                              shared_option_name, pure_c, self._build_types, self._options, ref)
        elif self._os_name == "FreeBSD":
            return get_linux_clang_builds(self._clang_versions, self._archs, shared_option_name,
                                          pure_c, self._build_types, self._options, ref)
        else:
            raise Exception("Unknown operating system: %s" % self._os_name)


class BuildConf(namedtuple("BuildConf", "settings options env_vars build_requires reference")):

    def __new__(cls, settings, options, env_vars, build_requires, reference):
        if not isinstance(settings, dict):
            raise Exception("'settings' field has to be a dict")
        if not isinstance(options, dict):
            raise Exception("'options' field has to be a dict")
        if not isinstance(env_vars, dict):
            raise Exception("'env_vars' field has to be a dict")
        if not isinstance(build_requires, dict):
            raise Exception("'build_requires' field has to be a dict")
        if reference is not None and not isinstance(reference, str) and \
           not isinstance(reference, ConanFileReference):
            raise Exception("'reference' field has to be a string or ConanFileReference")

        if isinstance(reference, str):
            reference = ConanFileReference.loads(reference)

        return super(BuildConf, cls).__new__(cls, settings, options, env_vars,
                                             build_requires, reference)


def get_mingw_builds(mingw_configurations, mingw_installer_reference,
                     archs, shared_option_name, build_types, options, reference=None):
    builds = []
    for config in mingw_configurations:
        version, arch, exception, thread = config
        if arch not in archs:
            continue
        settings = {"arch": arch, "compiler": "gcc",
                    "compiler.version": version[0:3],
                    "compiler.threads": thread,
                    "compiler.exception": exception}
        build_requires = {"*": [mingw_installer_reference]}

        if shared_option_name:
            for shared in [True, False]:
                opt = copy.copy(options)
                opt[shared_option_name] = shared
                builds += _make_mingw_builds(settings, opt, build_requires, build_types, reference)
        else:
            builds += _make_mingw_builds(settings, options, build_requires, build_types, reference)

    return builds


def _make_mingw_builds(settings, options, build_requires, build_types, reference=None):
    builds = []

    for build_type_it in build_types:
        s2 = copy.copy(settings)
        s2.update({"build_type": build_type_it})
        s2.update({"compiler.libcxx": "libstdc++"})
        builds.append(BuildConf(s2, options, {}, build_requires, reference))

    return builds


def get_visual_builds(visual_versions, archs, visual_runtimes, visual_toolsets, shared_option_name,
                      dll_with_static_runtime, vs10_x86_64_enabled, build_types, options,
                      reference=None):

    visual_toolsets = visual_toolsets or get_env_visual_toolsets()
    ret = []
    for visual_version in visual_versions:
        visual_version = str(visual_version)
        for arch in archs:
            if not vs10_x86_64_enabled and arch == "x86_64" and visual_version == "10":
                continue
            if not visual_toolsets or not visual_toolsets.get(visual_version):
                toolsets = [None]
            else:
                toolsets = visual_toolsets.get(visual_version)
            for toolset in toolsets:
                visual_builds = get_visual_builds_for_version(visual_runtimes, visual_version, arch,
                                                              shared_option_name,
                                                              dll_with_static_runtime, build_types,
                                                              options, reference, toolset=toolset)
                ret.extend(visual_builds)
    return ret


def get_visual_builds_for_version(visual_runtimes, visual_version, arch, shared_option_name,
                                  dll_with_static_runtime, build_types, options, reference=None,
                                  toolset=None):
    base_set = {"compiler": "Visual Studio",
                "compiler.version": visual_version,
                "arch": arch}

    if toolset:
        base_set["compiler.toolset"] = toolset
    sets = []

    debug_builds = set(['Debug'])
    release_builds = set(['Release', 'RelWithDebInfo', 'MinSizeRel'])

    runtime_build_map = {
        'MTd': debug_builds,
        'MDd': debug_builds,
        'MT': release_builds,
        'MD': release_builds,
    }

    build_types_set = set(build_types)

    for rt in visual_runtimes:
        compatible_builds = list(build_types_set.intersection(runtime_build_map[rt]))
        compatible_builds.sort() # so that it is deterministic.
        for bld in compatible_builds:
            if shared_option_name:
                opt = copy.copy(options)
                opt[shared_option_name] = False
                sets.append(({"build_type": bld, "compiler.runtime": rt},
                             opt, {}, {}))
                if rt in ['MT', 'MTd']:
                    if dll_with_static_runtime:
                        opt = copy.copy(options)
                        opt[shared_option_name] = True
                        sets.append(({"build_type": bld, "compiler.runtime": rt},
                                     opt, {}, {}))
                else:
                    opt = copy.copy(options)
                    opt[shared_option_name] = True
                    sets.append(({"build_type": bld, "compiler.runtime": rt},
                                 opt, {}, {}))
            else:
                sets.append(({"build_type": bld, "compiler.runtime": rt}, options, {}, {}))

    ret = []
    for setting, options, env_vars, build_requires in sets:
        tmp = copy.copy(base_set)
        tmp.update(setting)
        ret.append(BuildConf(tmp, options, env_vars, build_requires, reference))

    return ret


def get_build(compiler, the_arch, the_build_type, the_compiler_version,
              the_libcxx, options, reference):
    setts = {"arch": the_arch,
             "build_type": the_build_type,
             "compiler": compiler,
             "compiler.version": the_compiler_version}
    if the_libcxx:
        setts["compiler.libcxx"] = the_libcxx

    return BuildConf(setts, options, {}, {}, reference)


def get_osx_apple_clang_builds(apple_clang_versions, archs, shared_option_name,
                               pure_c, build_types, options, reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for compiler_version in apple_clang_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    opt = copy.copy(options)
                    opt[shared_option_name] = shared
                    for build_type_it in build_types:
                        if not pure_c:
                            ret.append(get_build("apple-clang", arch, build_type_it,
                                                 compiler_version,
                                                 "libc++", opt, reference))
                        else:
                            ret.append(get_build("apple-clang", arch, build_type_it,
                                                 compiler_version, None, opt, reference))
            else:
                for build_type_it in build_types:
                    if not pure_c:
                        ret.append(get_build("apple-clang", arch, build_type_it,
                                             compiler_version, "libc++", options, reference))
                    else:
                        ret.append(get_build("apple-clang", arch, build_type_it,
                                             compiler_version, None, options, reference))

    return ret


def get_linux_gcc_builds(gcc_versions, archs, shared_option_name, pure_c, build_types, options,
                         reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for gcc_version in gcc_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    opt = copy.copy(options)
                    opt[shared_option_name] = shared
                    for build_type_it in build_types:
                        if not pure_c:
                            ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                 "libstdc++", opt, reference))
                            if float(gcc_version) >= 5:
                                ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                     "libstdc++11", opt, reference))
                        else:
                            ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                 None, opt, reference))
            else:
                for build_type_it in build_types:
                    if not pure_c:
                        ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                             "libstdc++", options, reference))
                        if float(gcc_version) >= 5:
                            ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                 "libstdc++11", options, reference))
                    else:
                        ret.append(get_build("gcc", arch, build_type_it, gcc_version, None,
                                             options, reference))
    return ret


def get_linux_clang_builds(clang_versions, archs, shared_option_name, pure_c, build_types, options,
                           reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for clang_version in clang_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    opt = copy.copy(options)
                    opt[shared_option_name] = shared
                    for build_type_it in build_types:
                        if not pure_c:
                            ret.append(get_build("clang", arch, build_type_it, clang_version,
                                                 "libstdc++", opt, reference))
                            ret.append(get_build("clang", arch, build_type_it, clang_version,
                                                 "libc++", opt, reference))
                        else:
                            ret.append(get_build("clang", arch, build_type_it, clang_version,
                                                 None, opt, reference))
            else:
                for build_type_it in build_types:
                    if not pure_c:
                        ret.append(get_build("clang", arch, build_type_it, clang_version,
                                             "libstdc++", options, reference))
                        ret.append(get_build("clang", arch, build_type_it, clang_version,
                                             "libc++", options, reference))
                    else:
                        ret.append(get_build("clang", arch, build_type_it, clang_version,
                                             None, options, reference))
    return ret
