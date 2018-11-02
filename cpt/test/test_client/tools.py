import six
from conans.client.conan_api import Conan

from cpt.packager import ConanMultiPackager


def get_patched_multipackager(tc, *args, **kwargs):
    tc.init_dynamic_vars()
    conan_api = Conan(tc.client_cache, tc.user_io, tc.runner, tc.remote_manager, tc.hook_manager,
                      interactive=False)

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
