import os

from conans.client.conan_api import Conan
from conans.model.ref import ConanFileReference
from cpt.auth import AuthManager
from cpt.printer import Printer
from cpt.remotes import RemotesManager
from cpt.runner import CreateRunner, unscape_env
from cpt.uploader import Uploader


def run():
    # Get all from environ
    conan_api, client_cache, _ = Conan.factory()
    printer = Printer()
    if os.path.exists(client_cache.default_profile_path):
        os.remove(client_cache.default_profile_path)

    remotes_manager = RemotesManager(conan_api, printer)
    default_username = os.getenv("CONAN_USERNAME", None)
    auth_manager = AuthManager(conan_api, printer, default_username=default_username)

    uploader = Uploader(conan_api, remotes_manager, auth_manager, printer)
    profile_text = unscape_env(os.getenv("CPT_PROFILE"))
    args = os.getenv("CPT_ARGS", "")
    build_policy = unscape_env(os.getenv("CPT_BUILD_POLICY"))
    reference = ConanFileReference.loads(os.getenv("CONAN_REFERENCE"))
    conan_pip_package = unscape_env(os.getenv("CPT_PIP_PACKAGE"))

    runner = CreateRunner(profile_text, reference, conan_api, uploader,
                          args=args, conan_pip_package=conan_pip_package,
                          build_policy=build_policy)
    runner.run()

if __name__ == '__main__':
    run()
