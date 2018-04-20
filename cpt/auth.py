import os

from six import string_types

from cpt.printer import print_message


class AuthManager(object):

    def __init__(self, conan_api, login_input=None, passwords_input=None, default_username=None):
        """
        :param conan_api: ConanAPI
        :param login_input: Can be a string with the user or a dict with {"remote": "login"}
        :param passwords_input: Can be a string with the password or a dict with {"remote": "pass"}

        It also looks in the CONAN_LOGIN, CONAN_LOGIN_USERNAME, CONAN_USERNAME, CONAN_PASSWORD and
        CONAN_PASSWORD_XXXX
        """

        self._conan_api = conan_api
        self._data = {}  # {"remote_name": (user, password)}

        unique_login = self._get_single_login_username(login_input) or default_username
        unique_password = self._get_single_password(passwords_input)

        dict_login = self._get_multiple_logins(login_input)
        dict_password = self._get_multiple_passwords(passwords_input)

        if dict_login:
            if not dict_password:
                raise Exception("Invalid login/password parameter values, check README")

            for remote, username in dict_login.items():
                if remote not in dict_password:
                    raise Exception("Password for remote '%s' not specified" % remote)
                self._data[remote] = (username, dict_password[remote])
        elif unique_login:
            self._data[None] = (unique_login, unique_password)
        else:  # Try from environment
            raise Exception("Invalid login/password parameter values, check README")

    @staticmethod
    def _get_single_login_username(logins_input):
        if logins_input and isinstance(logins_input, string_types):
            return logins_input
        if os.getenv("CONAN_LOGIN_USERNAME"):
            return os.getenv("CONAN_LOGIN_USERNAME").replace('"', '\\"')
        if os.getenv("CONAN_USERNAME"):
            return os.getenv("CONAN_USERNAME").replace('"', '\\"')

    @staticmethod
    def _get_single_password(passwords_input):
        if passwords_input and isinstance(passwords_input, string_types):
            return passwords_input
        if not passwords_input and os.getenv("CONAN_PASSWORD"):
            return os.getenv("CONAN_PASSWORD").replace('"', '\\"')

    @staticmethod
    def _get_multiple_logins(logins_input):
        if logins_input and isinstance(logins_input, dict):
            return logins_input

        ret = {}
        for name in os.environ.keys():
            if name.startswith("CONAN_LOGIN_USERNAME_"):
                remote_name = name.split("_")[3]
                ret[remote_name] = os.environ[name]
        return ret

    @staticmethod
    def _get_multiple_passwords(passwords_input):
        if passwords_input and isinstance(passwords_input, dict):
            return passwords_input

        ret = {}
        for name in os.environ.keys():
            if name.startswith("CONAN_PASSWORD_"):
                remote_name = name.split("_")[2]
                ret[remote_name] = os.environ[name].replace('"', '\\"')
        return ret

    def get_user_password(self, remote=None):
        if None in self._data:  # General user and password for the same remote
            return self._data[None]
        if remote not in self._data:
            raise Exception("User and password for remote '%s' not specified" % remote)
        return self._data[remote]

    def login(self, remote_name):
        print_message("Verifying credentials...")
        user, password = self.get_user_password(remote_name)
        self._conan_api.authenticate(user, password, remote_name)
        print_message("OK! '%s' user logged in '%s' " % (user, password))

    def env_vars(self):
        ret = {}
        if None in self._data:
            ret["CONAN_LOGIN_USERNAME"], ret["CONAN_PASSWORD"] = self._data[None]
            return ret

        for remote, (login, password) in self._data.items():
            ret["CONAN_LOGIN_USERNAME_%s" % remote] = login
            ret["CONAN_PASSWORD_%s" % remote] = password

        return ret


