import six
from conans.client.conan_api import Conan
from conans.model.version import Version
from cpt import get_client_version

from cpt.packager import ConanMultiPackager


def get_patched_multipackager(tc, *args, **kwargs):
    client_version = get_client_version()
    extra_init_kwargs = {}
    if Version("1.11") < Version(client_version) < Version("1.18"):
        extra_init_kwargs.update({'requester': tc.requester})
    elif Version(client_version) >= Version("1.18"):
        extra_init_kwargs.update({'http_requester': tc.requester})

    if Version(client_version) < Version("1.12.0"):
        cache = tc.client_cache
    else:
        cache = tc.cache

    conan_api = Conan(cache_folder=cache.cache_folder, output=tc.out, **extra_init_kwargs)

    class Printer(object):

        def __init__(self, tc):
            self.tc = tc

        def __call__(self, contents):
            if six.PY2:
                contents = unicode(contents)
            self.tc.out.write(contents)

    kwargs["out"] = Printer(tc)
    kwargs["conan_api"] = conan_api
    kwargs["cwd"] = tc.current_folder

    mp = ConanMultiPackager(*args, **kwargs)
    return mp
