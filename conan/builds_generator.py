import copy
import os
from collections import namedtuple

BuildConf = namedtuple("BuildConf", "settings options env_vars build_requires")


def get_mingw_builds(mingw_configurations):
    builds = []
    for config in mingw_configurations:
        version, arch, exception, thread = config
        settings = {"arch": arch, "compiler": "gcc",
                    "compiler.version": version[0:3],
                    "compiler.threads": thread,
                    "compiler.exception": exception}
        settings.update({"compiler.libcxx": "libstdc++"})
        settings.update({"build_type": "Release"})
        builds.append((settings, {}))
        s2 = copy.copy(settings)
        s2.update({"build_type": "Debug"})
        builds.append(BuildConf(s2, {}, {}, {}))
    return builds


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
            sets.append(BuildConf({"build_type": "Release", "compiler.runtime": "MT"},
                                  {shared_option_name: False}, {}, {}))
            if dll_with_static_runtime:
                sets.append(BuildConf({"build_type": "Release", "compiler.runtime": "MT"},
                                      {shared_option_name: True}, {}, {}))
        if "MTd" in visual_runtimes:
            sets.append(BuildConf({"build_type": "Debug", "compiler.runtime": "MTd"},
                                  {shared_option_name: False}, {}, {}))
            if dll_with_static_runtime:
                sets.append(BuildConf({"build_type": "Debug", "compiler.runtime": "MTd"},
                                      {shared_option_name: True}, {}, {}))
        if "MD" in visual_runtimes:
            sets.append(BuildConf({"build_type": "Release", "compiler.runtime": "MD"},
                                  {shared_option_name: False}, {}, {}))
            sets.append(BuildConf({"build_type": "Release", "compiler.runtime": "MD"},
                                  {shared_option_name: True}, {}, {}))
        if "MDd" in visual_runtimes:
            sets.append(BuildConf({"build_type": "Debug", "compiler.runtime": "MDd"},
                                  {shared_option_name: False}, {}, {}))
            sets.append(BuildConf({"build_type": "Debug", "compiler.runtime": "MDd"},
                                  {shared_option_name: True}, {}, {}))

    else:
        if "MT" in visual_runtimes:
            sets.append(BuildConf({"build_type": "Release", "compiler.runtime": "MT"}, {}, {}, {}))
        if "MTd" in visual_runtimes:
            sets.append(BuildConf({"build_type": "Debug", "compiler.runtime": "MTd"}, {}, {}, {}))
        if "MDd" in visual_runtimes:
            sets.append(BuildConf({"build_type": "Debug", "compiler.runtime": "MDd"}, {}, {}, {}))
        if "MD" in visual_runtimes:
            sets.append(BuildConf({"build_type": "Release", "compiler.runtime": "MD"}, {}, {}, {}))

    ret = []
    for setting, options, env_vars, build_requires in sets:
        tmp = copy.copy(base_set)
        tmp.update(setting)
        ret.append(tmp, options, env_vars, build_requires)

    return ret


def get_osx_apple_clang_builds(apple_clang_versions, archs, shared_option_name, pure_c):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for compiler_version in apple_clang_versions:
        for arch in archs:
            if shared_option_name:
                for shared in [True, False]:
                    for build_type in ["Debug", "Release"]:
                        if not pure_c:
                            ret.append(BuildConf({"arch": arch,
                                                  "build_type": build_type,
                                                  "compiler": "apple-clang",
                                                  "compiler.version": compiler_version,
                                                  "compiler.libcxx": "libc++"},
                                                 {shared_option_name: shared}, {}, {}))
                        else:
                            ret.append(BuildConf({"arch": arch,
                                                  "build_type": build_type,
                                                  "compiler": "apple-clang",
                                                  "compiler.version": compiler_version},
                                                 {shared_option_name: shared}, {}, {}))
            else:
                for build_type in ["Debug", "Release"]:
                    if not pure_c:
                        ret.append(BuildConf({"arch": arch,
                                              "build_type": build_type,
                                              "compiler": "apple-clang",
                                              "compiler.version": compiler_version,
                                              "compiler.libcxx": "libc++"}, {}, {}, {}))
                    else:
                        ret.append(BuildConf({"arch": arch,
                                              "build_type": build_type,
                                              "compiler": "apple-clang",
                                              "compiler.version": compiler_version}, {}, {}, {}))
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
                            ret.append(BuildConf({"arch": arch,
                                                  "build_type": build_type,
                                                  "compiler": "gcc",
                                                  "compiler.version": gcc_version,
                                                  "compiler.libcxx": "libstdc++"},
                                                 {shared_option_name: shared}, {}, {}))
                            if float(gcc_version) > 5:
                                ret.append(BuildConf({"arch": arch,
                                                      "build_type": build_type,
                                                      "compiler": "gcc",
                                                      "compiler.version": gcc_version,
                                                      "compiler.libcxx": "libstdc++11"},
                                                      {shared_option_name: shared}, {}, {}))
                        else:
                            ret.append(BuildConf({"arch": arch,
                                                  "build_type": build_type,
                                                  "compiler": "gcc",
                                                  "compiler.version": gcc_version},
                                                 {shared_option_name: shared}, {}, {}))
            else:
                for build_type in ["Debug", "Release"]:
                    if not pure_c:
                        ret.append(BuildConf({"arch": arch,
                                              "build_type": build_type,
                                              "compiler": "gcc",
                                              "compiler.version": gcc_version,
                                              "compiler.libcxx": "libstdc++"}, {}, {}, {}))
                        if float(gcc_version) > 5:
                            ret.append(BuildConf({"arch": arch,
                                                  "build_type": build_type,
                                                  "compiler": "gcc",
                                                  "compiler.version": gcc_version,
                                                  "compiler.libcxx": "libstdc++11"}, {}, {}, {}))
                    else:
                        ret.append(BuildConf({"arch": arch,
                                              "build_type": build_type,
                                              "compiler": "gcc",
                                              "compiler.version": gcc_version}, {}, {}, {}))

    return ret