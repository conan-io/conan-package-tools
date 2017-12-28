import copy
from collections import namedtuple

from conans.model.ref import ConanFileReference


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
                     archs, shared_option_name, build_types, reference=None):
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
        options = {}

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


def get_visual_builds(visual_versions, archs, visual_runtimes, shared_option_name,
                      dll_with_static_runtime, vs10_x86_64_enabled, build_types, reference=None):
    ret = []
    for visual_version in visual_versions:
        visual_version = str(visual_version)
        for arch in archs:
            if not vs10_x86_64_enabled and arch == "x86_64" and visual_version == "10":
                continue
            visual_builds = get_visual_builds_for_version(visual_runtimes, visual_version, arch,
                                                          shared_option_name,
                                                          dll_with_static_runtime, build_types,
                                                          reference)

            ret.extend(visual_builds)
    return ret


def get_visual_builds_for_version(visual_runtimes, visual_version, arch, shared_option_name,
                                  dll_with_static_runtime, build_types, reference=None):
    base_set = {"compiler": "Visual Studio",
                "compiler.version": visual_version,
                "arch": arch}
    sets = []

    if shared_option_name:
        if "MT" in visual_runtimes and "Release" in build_types:
            sets.append(({"build_type": "Release", "compiler.runtime": "MT"},
                         {shared_option_name: False}, {}, {}))
            if dll_with_static_runtime:
                sets.append(({"build_type": "Release", "compiler.runtime": "MT"},
                             {shared_option_name: True}, {}, {}))
        if "MTd" in visual_runtimes and "Debug" in build_types:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MTd"},
                                  {shared_option_name: False}, {}, {}))
            if dll_with_static_runtime:
                sets.append(({"build_type": "Debug", "compiler.runtime": "MTd"},
                                      {shared_option_name: True}, {}, {}))
        if "MD" in visual_runtimes and "Release" in build_types:
            sets.append(({"build_type": "Release", "compiler.runtime": "MD"},
                                  {shared_option_name: False}, {}, {}))
            sets.append(({"build_type": "Release", "compiler.runtime": "MD"},
                                  {shared_option_name: True}, {}, {}))
        if "MDd" in visual_runtimes and "Debug" in build_types:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MDd"},
                                  {shared_option_name: False}, {}, {}))
            sets.append(({"build_type": "Debug", "compiler.runtime": "MDd"},
                                  {shared_option_name: True}, {}, {}))

    else:
        if "MT" in visual_runtimes and "Release" in build_types:
            sets.append(({"build_type": "Release", "compiler.runtime": "MT"}, {}, {}, {}))
        if "MTd" in visual_runtimes and "Debug" in build_types:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MTd"}, {}, {}, {}))
        if "MDd" in visual_runtimes and "Debug" in build_types:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MDd"}, {}, {}, {}))
        if "MD" in visual_runtimes and "Release" in build_types:
            sets.append(({"build_type": "Release", "compiler.runtime": "MD"}, {}, {}, {}))

    ret = []
    for setting, options, env_vars, build_requires in sets:
        tmp = copy.copy(base_set)
        tmp.update(setting)
        ret.append(BuildConf(tmp, options, env_vars, build_requires, reference))

    return ret


def get_build(compiler, the_arch, the_build_type, the_compiler_version,
              the_libcxx, the_shared_option_name,
              the_shared, reference):
    options = {}
    if the_shared_option_name:
        options = {the_shared_option_name: the_shared}
    setts = {"arch": the_arch,
             "build_type": the_build_type,
             "compiler": compiler,
             "compiler.version": the_compiler_version}
    if the_libcxx:
        setts["compiler.libcxx"] = the_libcxx

    return BuildConf(setts, options, {}, {}, reference)


def get_osx_apple_clang_builds(apple_clang_versions, archs, shared_option_name,
                               pure_c, build_types, reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for compiler_version in apple_clang_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    for build_type_it in build_types:
                        if not pure_c:
                            ret.append(get_build("apple-clang", arch, build_type_it,
                                                 compiler_version,
                                                 "libc++", shared_option_name, shared, reference))
                        else:
                            ret.append(get_build("apple-clang", arch, build_type_it,
                                                 compiler_version, None, shared_option_name,
                                                 shared, reference))
            else:
                for build_type_it in build_types:
                    if not pure_c:
                        ret.append(get_build("apple-clang", arch, build_type_it,
                                             compiler_version, "libc++", None, None, reference))
                    else:
                        ret.append(get_build("apple-clang", arch, build_type_it,
                                             compiler_version, None, None, None, reference))

    return ret


def get_linux_gcc_builds(gcc_versions, archs, shared_option_name, pure_c, build_types,
                         reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for gcc_version in gcc_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    for build_type_it in build_types:
                        if not pure_c:
                            ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                 "libstdc++", shared_option_name, shared,
                                                 reference))
                            if float(gcc_version) >= 5:
                                ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                     "libstdc++11", shared_option_name, shared,
                                                     reference))
                        else:
                            ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                 None, shared_option_name, shared, reference))
            else:
                for build_type_it in build_types:
                    if not pure_c:
                        ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                             "libstdc++", None, None, reference))
                        if float(gcc_version) >= 5:
                            ret.append(get_build("gcc", arch, build_type_it, gcc_version,
                                                 "libstdc++11", None, None, reference))
                    else:
                        ret.append(get_build("gcc", arch, build_type_it, gcc_version, None,
                                             None, None, reference))
    return ret


def get_linux_clang_builds(clang_versions, archs, shared_option_name, pure_c, build_types,
                           reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for clang_version in clang_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    for build_type_it in build_types:
                        if not pure_c:
                            ret.append(get_build("clang", arch, build_type_it, clang_version,
                                                 "libstdc++", shared_option_name, shared,
                                                 reference))
                            ret.append(get_build("clang", arch, build_type_it, clang_version,
                                                 "libc++", shared_option_name, shared, reference))
                        else:
                            ret.append(get_build("clang", arch, build_type_it, clang_version,
                                                 None, shared_option_name, shared, reference))
            else:
                for build_type_it in build_types:
                    if not pure_c:
                        ret.append(get_build("clang", arch, build_type_it, clang_version,
                                             "libstdc++", None, None, reference))
                        ret.append(get_build("clang", arch, build_type_it, clang_version,
                                             "libc++", None, None, reference))
                    else:
                        ret.append(get_build("clang", arch, build_type_it, clang_version,
                                             None, None, None, reference))
    return ret
