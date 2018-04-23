import unittest

from conans import tools
from conans.test.utils.tools import TestBufferConanOutput
from cpt.auth import AuthManager
from cpt.printer import Printer
from cpt.test.unit.packager_test import MockConanAPI


class AuthTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()
        self.output = TestBufferConanOutput()
        self.printer = Printer(self.output.write)

    def no_credentials_test(self):
        manager = AuthManager(self.conan_api, self.printer)
        user, password = manager.get_user_password()
        self.assertEquals(user, None)
        self.assertEquals(password, None)

    def test_plain_credentials(self):

        # Without default
        manager = AuthManager(self.conan_api, self.printer, login_input="myuser",
                              passwords_input="mypassword")

        user, password = manager.get_user_password("any")
        self.assertEquals(user, "myuser")
        self.assertEquals(password, "mypassword")

        user, password = manager.get_user_password(None)
        self.assertEquals(user, "myuser")
        self.assertEquals(password, "mypassword")

        # Only password is discarded
        manager = AuthManager(self.conan_api, self.printer, passwords_input="mypassword")
        user, password = manager.get_user_password()
        self.assertEquals(user, None)
        self.assertEquals(password, None)

        # With default
        manager = AuthManager(self.conan_api, self.printer,
                              passwords_input="mypassword",
                              default_username="myuser")

        user, password = manager.get_user_password("any")
        self.assertEquals(user, "myuser")
        self.assertEquals(password, "mypassword")

    def plain_from_env_test(self):
        with tools.environment_append({"CONAN_LOGIN_USERNAME": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            manager = AuthManager(self.conan_api, self.printer)
            user, password = manager.get_user_password()
            self.assertEquals(user, "myuser")
            self.assertEquals(password, "mypass")

    def plain_multiple_from_env_test(self):
        # Bad mix
        with tools.environment_append({"CONAN_LOGIN_USERNAME_R1": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            with self.assertRaisesRegexp(Exception, "Password for remote 'R1' not specified"):
                AuthManager(self.conan_api, self.printer)

        with tools.environment_append({"CONAN_LOGIN_USERNAME_R1": "myuser",
                                       "CONAN_PASSWORD_R1": "mypass",
                                       "CONAN_LOGIN_USERNAME_R_OTHER": "myuser2",
                                       "CONAN_PASSWORD_R_OTHER": "mypass2"}):
            manager = AuthManager(self.conan_api, self.printer)
            user, password = manager.get_user_password("r1")
            self.assertEquals(user, "myuser")
            self.assertEquals(password, "mypass")

            user, password = manager.get_user_password("r_other")
            self.assertEquals(user, "myuser2")
            self.assertEquals(password, "mypass2")

        # Miss password
        with tools.environment_append({"CONAN_LOGIN_USERNAME_R1": "myuser",
                                       "CONAN_PASSWORD_R2": "mypass"}):
            with self.assertRaisesRegexp(Exception, "Password for remote 'R1' not specified"):
                AuthManager(self.conan_api, self.printer)

    def plain_from_env_priority_test(self):
        with tools.environment_append({"CONAN_LOGIN_USERNAME": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            manager = AuthManager(self.conan_api, self.printer, login_input="otheruser",
                                  passwords_input="otherpass")
            user, password = manager.get_user_password()
            self.assertEquals(user, "otheruser")
            self.assertEquals(password, "otherpass")

    def plain_from_env_priority_mix_test(self):
        with tools.environment_append({"CONAN_LOGIN_USERNAME": "myuser",
                                       "CONAN_PASSWORD": "mypass"}):
            manager = AuthManager(self.conan_api, self.printer, login_input="otheruser")
            user, password = manager.get_user_password()
            self.assertEquals(user, "otheruser")
            self.assertEquals(password, "mypass")

    def test_dict_credentials(self):
        users = {"remote1": "my_user", "my_artifactory": "other_user"}
        passwords = {"remote1": "my_pass", "my_artifactory": "my_pass2"}
        manager = AuthManager(self.conan_api, self.printer, login_input=users,
                              passwords_input=passwords,
                              default_username=None)

        with self.assertRaisesRegexp(Exception, "User and password for remote "
                                                "'not_exist' not specified"):
            manager.get_user_password("not_exist")

        user, password = manager.get_user_password("my_artifactory")
        self.assertEquals(user, "other_user")
        self.assertEquals(password, "my_pass2")

        user, password = manager.get_user_password("remote1")
        self.assertEquals(user, "my_user")
        self.assertEquals(password, "my_pass")

        # Mix them
        with self.assertRaisesRegexp(Exception, "Specify a dict for 'login_username'"):
            AuthManager(self.conan_api, self.printer, passwords_input=passwords, default_username="peter")

    def test_env_vars_output(self):
        users = {"remote1": "my_user", "my_artifactory": "other_user"}
        passwords = {"remote1": "my_pass", "my_artifactory": "my_pass2"}
        manager = AuthManager(self.conan_api, self.printer, login_input=users,
                              passwords_input=passwords)
        expected = {'CONAN_PASSWORD_REMOTE1': 'my_pass',
                    'CONAN_LOGIN_USERNAME_REMOTE1': 'my_user',
                    'CONAN_PASSWORD_MY_ARTIFACTORY': 'my_pass2',
                    'CONAN_LOGIN_USERNAME_MY_ARTIFACTORY': 'other_user'}
        self.assertEquals(manager.env_vars(), expected)

        with tools.environment_append(expected):
            manager = AuthManager(self.conan_api, self.printer)
            self.assertEquals(manager.env_vars(), expected)

        manager = AuthManager(self.conan_api, self.printer, login_input="myuser",
                              passwords_input="mypassword")
        expected = {'CONAN_PASSWORD': 'mypassword',
                    'CONAN_LOGIN_USERNAME': 'myuser'}

        self.assertEquals(manager.env_vars(), expected)
