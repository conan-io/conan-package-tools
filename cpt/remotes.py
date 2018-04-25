import os
from collections import namedtuple
from six import string_types


class Remote(namedtuple("Remote", "url use_ssl name")):

    def to_str(self):
        ret = self.url
        if self.use_ssl is not None:
            ret += "@%s" % self.use_ssl
        else:
            ret += "@True"
        if self.name:
            ret += "@%s" % self.name

        return ret


class RemotesManager(object):

    def __init__(self, conan_api, printer, remotes_input=None, upload_input=None):
        self._conan_api = conan_api
        self._remotes = []
        self._upload = None
        self.printer = printer

        if remotes_input:
            if isinstance(remotes_input, string_types):
                for n, r in enumerate(remotes_input.split(",")):
                    self._remotes.append(Remote(r.strip(), True, "remote%s" % n))
            elif hasattr(remotes_input, '__iter__'):
                for n, r in enumerate(remotes_input):
                    if isinstance(r, string_types):
                        self._remotes.append(self._get_remote_from_str(r, "remotes", name="remote%s" % n))
                    elif len(r) == 2:
                        self._remotes.append(Remote(r[0].strip(), r[1], "remote%s" % n))
                    elif len(r) == 3:
                        self._remotes.append(Remote(r[0].strip(), r[1], r[2].strip()))
        else:  # Look env
            remotes_input = os.getenv("CONAN_REMOTES", [])
            if remotes_input:
                for n, r in enumerate(remotes_input.split(",")):
                    remote = self._get_remote_from_str(r, "CONAN_REMOTES", "remote%s" % n)
                    self._remotes.append(remote)

        if upload_input:
            if isinstance(upload_input, string_types):
                self._upload = Remote(upload_input, True, "upload_repo")
            elif hasattr(upload_input, '__iter__'):
                if len(upload_input) != 3:
                    raise Exception("Incorrect 'upload' argument, check README")
                self._upload = Remote(*upload_input)
        else:  # Look env
            tmp = os.getenv("CONAN_UPLOAD")
            if tmp in ("0", "None", "False"):
                tmp = None
            elif tmp == "1":
                raise Exception("WARNING! 'upload' argument has changed. Use 'upload' argument or "
                                "CONAN_UPLOAD environment variable to specify a remote URL to "
                                "upload your packages. e.j: "
                                "upload='https://api.bintray.com/conan/myuser/myconanrepo'")
            if tmp:
                self._upload = self._get_remote_from_str(tmp, "CONAN_UPLOAD", "upload_repo")

    def upload_remote_in_remote_list(self):
        if not self._upload:
            return False
        for r in self._remotes:
            if r.url == self._upload.url:
                return True
        return False

    def add_remotes_to_conan(self):
        _added_remotes = []
        for r in self._remotes:
            if self._upload and r.url == self._upload.url:
                name = self._add_remote(self._upload.url, self._upload.use_ssl,
                                        self._upload.name, insert=-1)
            else:
                name = self._add_remote(r.url, r.use_ssl, r.name, insert=-1)

            if name != r.name:    # Already existing url, keep it
                _added_remotes.append(Remote(r.url, r.use_ssl, name))
            else:
                _added_remotes.append(r)

        if self._upload and not self.upload_remote_in_remote_list():
            name = self._add_remote(self._upload.url, self._upload.use_ssl,
                                    self._upload.name, insert=-1)
            if name != self._upload.name:  # Already existing url, keep it
                self._upload = Remote(self._upload.url, self._upload.use_ssl, name)

        self._remotes = _added_remotes

    @staticmethod
    def _get_remote_from_str(the_str, var_name, name=None):
        tmp = the_str.split("@")
        if len(tmp) == 1:  # only URL
            return Remote(tmp[0].strip(), True, name)
        elif len(tmp) == 2:  # With SSL flag
            return Remote(tmp[0].strip(), tmp[1] not in (None, "0", "None", "False"), name)
        elif len(tmp) == 3:  # With SSL flag and name
            return Remote(tmp[0].strip(), tmp[1] not in (None, "0", "None", "False"), tmp[2].strip())
        else:
            raise Exception("Invalid %s env var format, check README" % var_name)

    def _get_remote_by_url(self, remote_url):
        remotes = self._conan_api.remote_list()
        for remote in remotes:
            if remote.url == remote_url:
                return remote.name, remotes
        return None, remotes

    def _get_remote_by_name(self, remotes, name):
        for remote in remotes:
            if remote.name == name:
                return remote
        return None

    def _add_remote(self, url, verify_ssl, name, insert=False):

        remote, remote_list = self._get_remote_by_url(url)
        if remote:
            self.printer.print_message("Remote for URL '%s' already exist, "
                                       "keeping the current remote and its name" % url)
            return remote

        remote = self._get_remote_by_name(remote_list, name)
        # If name is duplicated, but the url is not equal, remove it before adding it
        # A rename won't be good, because the remote is really different, it happens in local
        # when "upload_repo" is kept
        if remote:
            self._conan_api.remote_remove(name)

        self._conan_api.remote_add(name, url, verify_ssl=verify_ssl, insert=insert)
        return name

    @property
    def upload_remote_name(self):
        if not self._upload:
            return None
        return self._upload.name

    def named_remotes(self):
        if not self._remotes:
            return False
        return self._remotes[0].name

    def env_vars(self):
        ret = {}
        if self._upload:
            ret["CONAN_UPLOAD"] = self._upload.to_str()

        tmp = []
        if self.named_remotes():
            for remote in self._remotes:
                tmp.append(remote.to_str())
        ret["CONAN_REMOTES"] = ",".join(tmp)
        return ret
