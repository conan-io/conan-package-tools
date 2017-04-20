import copy
from collections import namedtuple

BuildConf = namedtuple("BuildConf", "settings options env_vars build_requires")


def get_mingw_builds(mingw_configurations, mingw_installer_reference, archs):
    builds = []
    for config in mingw_configurations:
        version, arch, exception, thread = config
        if arch not in archs:
            continue
        settings = {"arch": arch, "compiler": "gcc",
                    "compiler.version": version[0:3],
                    "compiler.threads": thread,
                    "compiler.exception": exception}
        options, build_requires = _add_mingw_build_require(settings, mingw_installer_reference)

        settings.update({"compiler.libcxx": "libstdc++"})
        settings.update({"build_type": "Release"})
        builds.append(BuildConf(settings, options, {}, build_requires))
        s2 = copy.copy(settings)
        s2.update({"build_type": "Debug"})

        builds.append(BuildConf(s2, options, {}, build_requires))
    return builds


def _add_mingw_build_require(settings, mingw_installer_reference):
    installer_options = {}
    for setting in ("compiler.threads", "compiler.exception", "compiler.version", "arch"):
        setting_value = settings.get(setting, None)
        if setting_value:
            short_name = setting.split(".", 1)[-1]
            option_name = "%s:%s" % (mingw_installer_reference.name, short_name)
            installer_options[option_name] = setting_value

    return installer_options, {"*": [mingw_installer_reference]}


def get_visual_builds(visual_versions, archs, visual_runtimes, shared_option_name,
                      dll_with_static_runtime, vs10_x86_64_enabled):
    ret = []
    for visual_version in visual_versions:
        visual_version = str(visual_version)
        for arch in archs:
            if not vs10_x86_64_enabled and arch == "x86_64" and visual_version == "10":
                continue
            visual_builds = get_visual_builds_for_version(visual_runtimes, visual_version, arch,
                                                          shared_option_name, dll_with_static_runtime)

            ret.extend(visual_builds)
    return ret


def get_visual_builds_for_version(visual_runtimes, visual_version, arch, shared_option_name, dll_with_static_runtime):
    base_set = {"compiler": "Visual Studio",
                "compiler.version": visual_version,
                "arch": arch}
    sets = []

    if shared_option_name:
        if "MT" in visual_runtimes:
            sets.append(({"build_type": "Release", "compiler.runtime": "MT"},
                         {shared_option_name: False}, {}, {}))
            if dll_with_static_runtime:
                sets.append(({"build_type": "Release", "compiler.runtime": "MT"},
                             {shared_option_name: True}, {}, {}))
        if "MTd" in visual_runtimes:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MTd"},
                                  {shared_option_name: False}, {}, {}))
            if dll_with_static_runtime:
                sets.append(({"build_type": "Debug", "compiler.runtime": "MTd"},
                                      {shared_option_name: True}, {}, {}))
        if "MD" in visual_runtimes:
            sets.append(({"build_type": "Release", "compiler.runtime": "MD"},
                                  {shared_option_name: False}, {}, {}))
            sets.append(({"build_type": "Release", "compiler.runtime": "MD"},
                                  {shared_option_name: True}, {}, {}))
        if "MDd" in visual_runtimes:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MDd"},
                                  {shared_option_name: False}, {}, {}))
            sets.append(({"build_type": "Debug", "compiler.runtime": "MDd"},
                                  {shared_option_name: True}, {}, {}))

    else:
        if "MT" in visual_runtimes:
            sets.append(({"build_type": "Release", "compiler.runtime": "MT"}, {}, {}, {}))
        if "MTd" in visual_runtimes:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MTd"}, {}, {}, {}))
        if "MDd" in visual_runtimes:
            sets.append(({"build_type": "Debug", "compiler.runtime": "MDd"}, {}, {}, {}))
        if "MD" in visual_runtimes:
            sets.append(({"build_type": "Release", "compiler.runtime": "MD"}, {}, {}, {}))

    ret = []
    for setting, options, env_vars, build_requires in sets:
        tmp = copy.copy(base_set)
        tmp.update(setting)
        ret.append(BuildConf(tmp, options, env_vars, build_requires))

    return ret


def get_build(compiler, the_arch, the_build_type, the_compiler_version, the_libcxx=None, the_shared_option_name=None, the_shared=None):
    options = {}
    if the_shared_option_name:
        options = {the_shared_option_name: the_shared}
    setts = {"arch": the_arch,
             "build_type": the_build_type,
             "compiler": compiler,
             "compiler.version": the_compiler_version}
    if the_libcxx:
        setts["compiler.libcxx"] = the_libcxx

    return BuildConf(setts, options, {}, {})


def get_osx_apple_clang_builds(apple_clang_versions, archs, shared_option_name, pure_c):
    ret = []

    # Not specified compiler or compiler version, will use the auto detected
    for compiler_version in apple_clang_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    for build_type in ["Debug", "Release"]:
                        if not pure_c:
                            ret.append(get_build("apple-clang", arch, build_type, compiler_version,
                                                 "libc++", shared_option_name, shared))
                        else:
                            ret.append(get_build("apple-clang", arch, build_type, compiler_version, None, shared_option_name, shared))
            else:
                for build_type in ["Debug", "Release"]:
                    if not pure_c:
                        ret.append(get_build("apple-clang", arch, build_type, compiler_version, "libc++"))
                    else:
                        ret.append(get_build("apple-clang", arch, build_type, compiler_version))

    return ret


def get_linux_gcc_builds(gcc_versions, archs, shared_option_name, pure_c):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for gcc_version in gcc_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    for build_type in ["Debug", "Release"]:
                        if not pure_c:
                            ret.append(get_build("gcc", arch, build_type, gcc_version,
                                                 "libstdc++", shared_option_name, shared))
                            if float(gcc_version) > 5:
                                ret.append(get_build("gcc", arch, build_type, gcc_version,
                                                     "libstdc++11", shared_option_name, shared))
                        else:
                            ret.append(get_build("gcc", arch, build_type, gcc_version,
                                                 None, shared_option_name, shared))
            else:
                for build_type in ["Debug", "Release"]:
                    if not pure_c:
                        ret.append(get_build("gcc", arch, build_type, gcc_version,
                                             "libstdc++"))
                        if float(gcc_version) > 5:
                            ret.append(get_build("gcc", arch, build_type, gcc_version,
                                                 "libstdc++11"))
                    else:
                        ret.append(get_build("gcc", arch, build_type, gcc_version))
    return ret
