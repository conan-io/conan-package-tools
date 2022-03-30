import os

from conans import tools
from conans.client.conan_api import Conan
from conans.model.ref import ConanFileReference
from conans.model.version import Version

from cpt.auth import AuthManager
from cpt.printer import Printer
from cpt.profiles import save_profile_to_tmp
from cpt.remotes import RemotesManager
from cpt.runner import CreateRunner, unscape_env
from cpt.uploader import Uploader
from cpt import get_client_version


def run():
    conan_version = get_client_version()
    if conan_version < Version("1.18.0"):
        conan_api, client_cache, _ = Conan.factory()
    else:
        conan_api, _, _ = Conan.factory()
        conan_api.create_app()
        client_cache = conan_api.app.cache

    printer = Printer()

    remotes_manager = RemotesManager(conan_api, printer)
    remotes_manager.add_remotes_to_conan()
    default_username = os.getenv("CONAN_USERNAME")
    auth_manager = AuthManager(conan_api, printer, default_username=default_username)

    upload_retry = os.getenv("CPT_UPLOAD_RETRY")
    upload_only_recipe = os.getenv("CPT_UPLOAD_ONLY_RECIPE")
    upload_force = os.getenv("CPT_UPLOAD_FORCE")
    uploader = Uploader(conan_api, remotes_manager, auth_manager, printer, upload_retry, upload_force)
    build_policy = unscape_env(os.getenv("CPT_BUILD_POLICY"))
    require_overrides = unscape_env(os.getenv("CPT_REQUIRE_OVERRIDES"))
    test_folder = unscape_env(os.getenv("CPT_TEST_FOLDER"))
    reference = ConanFileReference.loads(os.getenv("CONAN_REFERENCE"))

    profile_text = unscape_env(os.getenv("CPT_PROFILE"))
    abs_profile_path = save_profile_to_tmp(profile_text)
    base_profile_text = unscape_env(os.getenv("CPT_BASE_PROFILE"))
    profile_build_text = unscape_env(os.getenv("CPT_PROFILE_BUILD"))
    config_url = unscape_env(os.getenv("CPT_CONFIG_URL"))
    config_args = unscape_env(os.getenv("CPT_CONFIG_ARGS"))
    upload_dependencies = unscape_env(os.getenv("CPT_UPLOAD_DEPENDENCIES"))
    update_dependencies = unscape_env(os.getenv("CPT_UPDATE_DEPENDENCIES"))
    conanfile = unscape_env(os.getenv("CPT_CONANFILE"))
    lockfile = unscape_env(os.getenv("CPT_LOCKFILE"))
    skip_recipe_export = unscape_env(os.getenv("CPT_SKIP_RECIPE_EXPORT"))
    if base_profile_text:
        base_profile_name = unscape_env(os.getenv("CPT_BASE_PROFILE_NAME"))
        tools.save(os.path.join(client_cache.profiles_path, base_profile_name),
                   base_profile_text)
    if profile_build_text:
        abs_profile_build_path = save_profile_to_tmp(profile_build_text)
    else:
        abs_profile_build_path = None

    upload = os.getenv("CPT_UPLOAD_ENABLED")
    runner = CreateRunner(abs_profile_path, reference, conan_api, uploader,
                          build_policy=build_policy, require_overrides=require_overrides, printer=printer, upload=upload,
                          upload_only_recipe=upload_only_recipe,
                          test_folder=test_folder, config_url=config_url, config_args=config_args,
                          upload_dependencies=upload_dependencies, conanfile=conanfile,
                          skip_recipe_export=skip_recipe_export,
                          update_dependencies=update_dependencies,
                          lockfile=lockfile,
                          profile_build_abs_path=abs_profile_build_path)
    runner.run()


if __name__ == '__main__':
    run()
