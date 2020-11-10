
__version__ = '0.34.5-dev'
NEWEST_CONAN_SUPPORTED = "1.32.000"


def get_client_version():
    from conans.model.version import Version
    from conans import __version__ as client_version
    from os import getenv
    # It is a mess comparing dev versions, lets assume that the -dev is the further release
    if getenv("CONAN_TEST_SUITE", False):
        return Version(client_version)
    return Version(client_version.replace("-dev", ""))
