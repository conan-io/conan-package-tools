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
                     archs, build_types, common_options, reference=None):
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

        if common_options:
            for combination in _combine_common_options(common_options):
                builds += _make_mingw_builds(settings=settings,
                                             options=_option_dict_from_combination(combination),
                                             build_requires=build_requires,
                                             build_types=build_types,
                                             reference=reference)
        else:
            builds += _make_mingw_builds(settings=settings,
                                         options={},
                                         build_requires=build_requires,
                                         build_types=build_types,
                                         reference=reference)
    return builds


def _make_mingw_builds(settings, options, build_requires, build_types, reference=None):
    builds = []

    for build_type_it in build_types:
        s2 = copy.copy(settings)
        s2.update({"build_type": build_type_it})
        s2.update({"compiler.libcxx": "libstdc++"})
        builds.append(BuildConf(s2, options, {}, build_requires, reference))

    return builds


def get_visual_builds(visual_versions, archs, visual_runtimes,
                      dll_with_static_runtime, vs10_x86_64_enabled, build_types, common_options,
                      reference=None):
    ret = []
    for visual_version in visual_versions:
        visual_version = str(visual_version)
        for arch in archs:
            if not vs10_x86_64_enabled and arch == "x86_64" and visual_version == "10":
                continue
            visual_builds = get_visual_builds_for_version(visual_runtimes=visual_runtimes,
                                                          visual_version=visual_version,
                                                          arch=arch,
                                                          dll_with_static_runtime=dll_with_static_runtime,
                                                          build_types=build_types,
                                                          common_options=common_options,
                                                          reference=reference)

            ret.extend(visual_builds)
    return ret


def get_visual_builds_for_version(visual_runtimes, visual_version, arch, dll_with_static_runtime,
                                  build_types, common_options, reference=None):
    base_set = {"compiler": "Visual Studio",
                "compiler.version": visual_version,
                "arch": arch}

    sets = []
    shared_option_name = ""

    common_options_without_shared = dict()
    for key in common_options.keys():
        if "shared" in key.lower():
            shared_option_name = key
            common_options_without_shared = copy.copy(common_options)
            del common_options_without_shared[key]
            break

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
        if common_options_without_shared:
            for combination in _combine_common_options(common_options_without_shared):
                opt = copy.copy(options)
                opt.update(_option_dict_from_combination(combination))
                ret.append(BuildConf(tmp, opt, env_vars, build_requires, reference))
        else:
            ret.append(BuildConf(tmp, options, env_vars, build_requires, reference))
    return ret


def get_build(compiler, the_arch, the_build_type, the_compiler_version, the_libcxx, reference,
              common_options):
    options = common_options
    setts = {"arch": the_arch,
             "build_type": the_build_type,
             "compiler": compiler,
             "compiler.version": the_compiler_version}
    if the_libcxx:
        setts["compiler.libcxx"] = the_libcxx

    return BuildConf(setts, options, {}, {}, reference)


def get_osx_apple_clang_builds(apple_clang_versions, archs, pure_c, build_types, common_options,
                               reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for compiler_version in apple_clang_versions:
        for arch in archs:
            for build_type_it in build_types:
                if common_options:
                    for combination in _combine_common_options(common_options):
                        ret.append(get_build(compiler="apple-clang",
                                             the_arch=arch,
                                             the_build_type=build_type_it,
                                             the_compiler_version=compiler_version,
                                             the_libcxx="libc++" if not pure_c else None,
                                             reference=reference,
                                             common_options=_option_dict_from_combination(combination)))
                else:
                    ret.append(get_build(compiler="apple-clang",
                                         the_arch=arch,
                                         the_build_type=build_type_it,
                                         the_compiler_version=compiler_version,
                                         the_libcxx="libc++" if not pure_c else None,
                                         reference=reference,
                                         common_options={}))
    return ret


def _combine_common_options(common_options):
    """
    Get all the combinations for common options. Returns a list of tuples with the combination of
    key - value.

    Keyword arguments:
    common_options -- Dictionary with options and possible values as in a recipe: {"my_option": [True, False]}
    """

    expanded_options = list()
    for key in common_options:
        internal_list = list()
        for value in common_options[key]:
            internal_list.append((key, value))
        expanded_options.append(internal_list)

    combinations = list()
    if len(common_options) == 1:
        for option in expanded_options[0]:
            combinations.append(option)
        return combinations

    import itertools
    combinations = itertools.product(*expanded_options)
    return list(combinations)


def _option_dict_from_combination(combination):
    """
    Returns a dictionary with the fixed key-value from an option combination.

    Keyword arguments:
    combination -- List of tuples with the fixed combinations: (("shared", True), ("my_option", False))
    """
    option_dict = dict()
    try:
        for comb in combination:
            option_dict[comb[0]] = comb[1]
    except:
        option_dict.clear()
        option_dict[combination[0]] = combination[1]
    return option_dict


def get_linux_gcc_builds(gcc_versions, archs, pure_c, build_types, common_options, reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for gcc_version in gcc_versions:
        for arch in archs:
            for build_type_it in build_types:
                if common_options:
                    for combination in _combine_common_options(common_options):
                        if not pure_c:
                            ret.append(get_build(compiler="gcc",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=gcc_version,
                                                 the_libcxx="libstdc++", 
                                                 reference=reference,
                                                 common_options=_option_dict_from_combination(combination)))
                            if float(gcc_version) >= 5:
                                ret.append(get_build(compiler="gcc",
                                                     the_arch=arch,
                                                     the_build_type=build_type_it,
                                                     the_compiler_version=gcc_version,
                                                     the_libcxx="libstdc++11", 
                                                     reference=reference,
                                                     common_options=_option_dict_from_combination(combination)))
                        else:
                            ret.append(get_build(compiler="gcc",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=gcc_version,
                                                 the_libcxx=None, 
                                                 reference=reference,
                                                 common_options=_option_dict_from_combination(combination)))
                else:
                    if not pure_c:
                        ret.append(get_build(compiler="gcc",
                                             the_arch=arch,
                                             the_build_type=build_type_it,
                                             the_compiler_version=gcc_version,
                                             the_libcxx="libstdc++", 
                                             reference=reference,
                                             common_options={}))
                        if float(gcc_version) >= 5:
                            ret.append(get_build(compiler="gcc",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=gcc_version,
                                                 the_libcxx="libstdc++11", 
                                                 reference=reference,
                                                 common_options={}))
                    else:
                        ret.append(get_build(compiler="gcc",
                                             the_arch=arch,
                                             the_build_type=build_type_it,
                                             the_compiler_version=gcc_version,
                                             the_libcxx=None, 
                                             reference=reference,
                                             common_options={}))
    return ret


def get_linux_clang_builds(clang_versions, archs, pure_c, build_types, common_options,
                           reference=None):
    ret = []
    # Not specified compiler or compiler version, will use the auto detected
    for clang_version in clang_versions:
        for arch in archs:
            for build_type_it in build_types:
                if common_options:
                    for combination in _combine_common_options(common_options):
                        if not pure_c:
                            ret.append(get_build(compiler="clang",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=clang_version,
                                                 the_libcxx="libstdc++",
                                                 reference=reference,
                                                 common_options=_option_dict_from_combination(combination)))
                            ret.append(get_build(compiler="clang",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=clang_version,
                                                 the_libcxx="libc++",
                                                 reference=reference,
                                                 common_options=_option_dict_from_combination(combination)))
                        else:
                            ret.append(get_build(compiler="clang",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=clang_version,
                                                 the_libcxx=None,
                                                 reference=reference,
                                                 common_options=_option_dict_from_combination(combination)))
                else:
                    if not pure_c:
                            ret.append(get_build(compiler="clang",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=clang_version,
                                                 the_libcxx="libstdc++",
                                                 reference=reference,
                                                 common_options={}))
                            ret.append(get_build(compiler="clang",
                                                 the_arch=arch,
                                                 the_build_type=build_type_it,
                                                 the_compiler_version=clang_version,
                                                 the_libcxx="libc++",
                                                 reference=reference,
                                                 common_options={}))
                    else:
                        ret.append(get_build(compiler="clang",
                                                the_arch=arch,
                                                the_build_type=build_type_it,
                                                the_compiler_version=clang_version,
                                                the_libcxx=None,
                                                reference=reference,
                                                common_options={}))
    return ret
