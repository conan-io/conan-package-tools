
__version__ = '0.28.1'
NEWEST_CONAN_SUPPORTED = "1.17.0-dev"


def get_client_version():
    from conans.model.version import Version
    from conans import __version__ as client_version
    # It is a mess comparing dev versions, lets assume that the -dev is the further release
    return Version(client_version.replace("-dev", ""))
