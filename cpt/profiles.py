import os
import tempfile

from conans.client import tools
from conans.client.profile_loader import _load_profile
from conans.util.files import save


def get_profiles(client_cache, build_config, base_profile_name=None):

    base_profile_text = ""
    if base_profile_name:
        base_profile_path = os.path.join(client_cache.profiles_path, base_profile_name)
        base_profile_text = tools.load(base_profile_path)
    base_profile_name = base_profile_name or "default"
    tmp = """
include(%s)

[settings]
%s
[options]
%s
[env]
%s
[build_requires]
%s
"""

    def pairs_lines(items):
        return "\n".join(["%s=%s" % (k, v) for k, v in items])

    settings = pairs_lines(sorted(build_config.settings.items()))
    options = pairs_lines(build_config.options.items())
    env_vars = pairs_lines(build_config.env_vars.items())
    br_lines = ""
    for pattern, build_requires in build_config.build_requires.items():
        br_lines += "\n".join(["%s:%s" % (pattern, br) for br in build_requires])

    if os.getenv("CONAN_BUILD_REQUIRES"):
        brs = os.getenv("CONAN_BUILD_REQUIRES").split(",")
        brs = ['*:%s' % br.strip() if ":" not in br else br for br in brs]
        if br_lines:
            br_lines += "\n"
        br_lines += "\n".join(brs)

    profile_text = tmp % (base_profile_name, settings, options, env_vars, br_lines)
    return profile_text, base_profile_text


def patch_default_base_profile(conan_api, profile_abs_path):
    """If we have a profile including default, but the users default in config is that the default
    is other, we have to change the include"""
    text = tools.load(profile_abs_path)
    if "include(default)" in text:  # User didn't specified a custom profile
        default_profile_name = os.path.basename(conan_api._client_cache.default_profile_path)
        if not os.path.exists(conan_api._client_cache.default_profile_path):
            conan_api.create_profile(default_profile_name, detect=True)

        if default_profile_name != "default":  # User have a different default profile name
            # https://github.com/conan-io/conan-package-tools/issues/121
            text = text.replace("include(default)", "include(%s)" % default_profile_name)
            tools.save(profile_abs_path, text)


def save_profile_to_tmp(profile_text):
    # Save the profile in a tmp file
    tmp = os.path.join(tempfile.mkdtemp(suffix='conan_package_tools_profiles'), "profile")
    abs_profile_path = os.path.abspath(tmp)
    save(abs_profile_path, profile_text)
    return abs_profile_path


def load_profile(profile_abs_path, client_cache):
    text = tools.load(profile_abs_path)
    profile, _ = _load_profile(text, os.path.dirname(profile_abs_path),
                               client_cache.profiles_path)
    return profile

