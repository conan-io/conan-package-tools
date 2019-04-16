import os

from conans import tools
from conans.client.conan_api import Conan
from conans.model.ref import ConanFileReference

from cpt.auth import AuthManager
from cpt.printer import Printer
from cpt.profiles import save_profile_to_tmp
from cpt.remotes import RemotesManager
from cpt.runner import CreateRunner, unscape_env
from cpt.uploader import Uploader


def run():
    # Get all from environ
    conan_api, client_cache, _ = Conan.factory()
    printer = Printer()

    remotes_manager = RemotesManager(conan_api, printer)
    default_username = os.getenv("CONAN_USERNAME")
    auth_manager = AuthManager(conan_api, printer, default_username=default_username)

    upload_retry = os.getenv("CPT_UPLOAD_RETRY")
    upload_only_recipe = os.getenv("CPT_UPLOAD_ONLY_RECIPE")
    uploader = Uploader(conan_api, remotes_manager, auth_manager, printer, upload_retry)
    build_policy = unscape_env(os.getenv("CPT_BUILD_POLICY"))
    test_folder = unscape_env(os.getenv("CPT_TEST_FOLDER"))
    reference = ConanFileReference.loads(os.getenv("CONAN_REFERENCE"))

    profile_text = unscape_env(os.getenv("CPT_PROFILE"))
    abs_profile_path = save_profile_to_tmp(profile_text)
    base_profile_text = unscape_env(os.getenv("CPT_BASE_PROFILE"))
    config_url = unscape_env(os.getenv("CPT_CONFIG_URL"))
    upload_dependencies = unscape_env(os.getenv("CPT_UPLOAD_DEPENDENCIES"))
    conanfile = unscape_env(os.getenv("CPT_CONANFILE"))
    if base_profile_text:
        base_profile_name = unscape_env(os.getenv("CPT_BASE_PROFILE_NAME"))
        tools.save(os.path.join(client_cache.profiles_path, base_profile_name),
                   base_profile_text)

    upload = os.getenv("CPT_UPLOAD_ENABLED")
    runner = CreateRunner(abs_profile_path, reference, conan_api, uploader,
                          build_policy=build_policy, printer=printer, upload=upload,
                          upload_only_recipe=upload_only_recipe,
                          test_folder=test_folder, config_url=config_url,
                          upload_dependencies=upload_dependencies, conanfile=conanfile)
    runner.run()


if __name__ == '__main__':
    run()
