import os
from collections import namedtuple

from conans import tools
from conans.test.utils.test_files import temp_folder
from conans.util.files import save


class MockRunner(object):

    def __init__(self):
        self.reset()
        self.output = ""

    def reset(self):
        self.calls = []

    def __call__(self, command):
        self.calls.append(command)
        return 0


class MockConanCache(object):

    def __init__(self, *args, **kwargs):
        _base_dir = temp_folder()
        self.default_profile_path = os.path.join(_base_dir, "default")
        self.profiles_path = _base_dir

Action = namedtuple("Action", "name args kwargs")


class MockConanAPI(object):

    def __init__(self):
        self.calls = []
        self._client_cache = MockConanCache()

    def create(self, *args, **kwargs):
        self.calls.append(Action("create", args, kwargs))

    def create_profile(self, *args, **kwargs):
        save(os.path.join(self._client_cache.profiles_path, args[0]), "[settings]")
        self.calls.append(Action("create_profile", args, kwargs))

    def remote_list(self, *args, **kwargs):
        self.calls.append(Action("remote_list", args, kwargs))
        return []

    def remote_add(self, *args, **kwargs):
        self.calls.append(Action("remote_add", args, kwargs))
        return args[0]

    def authenticate(self, *args, **kwargs):
        self.calls.append(Action("authenticate", args, kwargs))

    def upload(self, *args, **kwargs):
        self.calls.append(Action("upload", args, kwargs))

    def get_profile_from_call_index(self, number):
        call = self.calls[number]
        return self.get_profile_from_call(call)

    def get_profile_from_call(self, call):
        if call.name != "create":
            raise Exception("Invalid test, not contains a create: %s" % self.calls)
        from conans.client.profile_loader import read_profile
        profile_name = call.kwargs["profile_name"]
        tools.replace_in_file(profile_name, "include", "#include")
        return read_profile(profile_name, os.path.dirname(profile_name), None)[0]

    def reset(self):
        self.calls = []

    def _get_creates(self):
        return [call for call in self.calls if call.name == "create"]

    def assert_tests_for(self, indexes):
        creates = self._get_creates()
        for create_index, index in enumerate(indexes):
            profile = self.get_profile_from_call(creates[create_index])
            assert("os%s" % index == profile.settings["os"])


class MockCIManager(object):

    def __init__(self, current_branch=None, build_policy=None, skip_builds=False, is_pull_request=False):
        self._current_branch = current_branch
        self._build_policy = build_policy
        self._skip_builds = skip_builds
        self._is_pr = is_pull_request

    def get_commit_build_policy(self):
        return self._build_policy

    def skip_builds(self):
        return self._skip_builds

    def is_pull_request(self):
        return self._is_pr

    def get_branch(self):
        return self._current_branch
