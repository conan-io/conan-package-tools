from conans import tools

from conans.client.conan_api import Conan
from cpt.runner import TestPackageRunner


def run():
    _, client_cache, _ = Conan.factory()
    tools.rmdir(client_cache.default_profile_path)
    runner = TestPackageRunner()
    runner.run()

if __name__ == '__main__':
    run()
