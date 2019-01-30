import six
from conans import __version__ as client_version
from conans import __version__ as conan_version
from conans.client.conan_api import Conan
from conans.model.version import Version

from cpt.packager import ConanMultiPackager


def get_patched_multipackager(tc, *args, **kwargs):
    tc.init_dynamic_vars()

    extra_init_kwargs = {}
    if Version(client_version) >= Version("1.11"):
        extra_init_kwargs.update({'requester': tc.requester})

    if Version(conan_version) < Version("1.12.0"):
        cache = tc.client_cache
    else:
        cache = tc.cache

    conan_api = Conan(cache, tc.user_io, tc.runner, tc.remote_manager, tc.hook_manager,
                      interactive=False, **extra_init_kwargs)

    class Printer(object):

        def __init__(self, tc):
            self.tc = tc

        def __call__(self, contents):
            if six.PY2:
                contents = unicode(contents)
            self.tc.user_io.out._buffer.write(contents)

    kwargs["out"] = Printer(tc)
    kwargs["conan_api"] = conan_api
    kwargs["cwd"] = tc.current_folder

    mp = ConanMultiPackager(*args, **kwargs)
    return mp
