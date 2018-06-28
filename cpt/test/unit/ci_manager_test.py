import unittest
import os

from conans.test.utils.tools import TestBufferConanOutput
from cpt.packager import ConanMultiPackager
from cpt.ci_manager import CIManager
from conans import tools
from cpt.printer import Printer


class CIManagerTest(unittest.TestCase):

    def setUp(self):
        # Clean env first
        new_env = {}
        for var, value in os.environ.items():
            if "travis" not in var.lower() and \
               "appveyor" not in var.lower() and \
               "bamboo" not in var.lower():
                new_env[var] = value

        os.environ = new_env
        self.output = TestBufferConanOutput()
        self.printer = Printer(self.output.write)

    def test_skip(self):
        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE": "[skip ci]",
                                       "TRAVIS_BRANCH": "mybranch",
                                       }):
            packager = ConanMultiPackager(username="dori", reference="lib/1.0")
            # Constructor skipped
            ret = packager.run()
            self.assertEquals(ret, 99)

    def test_instance_correct(self):
        # Bamboo
        with tools.environment_append({"bamboo_buildNumber": "xx",
                                       "bamboo_planRepository_branch": "mybranch"}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())

        # Travis
        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE": "msg",
                                       "TRAVIS_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertEquals(manager.get_commit_msg(), "msg")

        # Appveyor
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED": "more",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertEquals(manager.get_commit_msg(), "msg more")

        # Appveyor PULL REQUEST
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_PULL_REQUEST_NUMBER": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED": "more",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertIsNone(manager.get_branch())
            self.assertEquals(manager.get_commit_msg(), "msg more")

        # Appveyor no extended
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_PULL_REQUEST_NUMBER": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertIsNone(manager.get_branch())
            self.assertEquals(manager.get_commit_msg(), "msg")

        # Circle CI
        with tools.environment_append({"CIRCLECI": "1",
                                       "CIRCLE_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())

        # Gitlab
        with tools.environment_append({"GITLAB_CI": "1",
                                       "CI_BUILD_REF_NAME": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())

        # Jenkins
        with tools.environment_append({"JENKINS_URL": "1",
                                       "BRANCH_NAME": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())

    def test_build_policy(self):
        # Travis
        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE":
                                           "This is a great commit [build=outdated] End."}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), "outdated")
            self.assertEquals(manager.get_commit_msg(), "This is a great commit "
                                                        "[build=outdated] End.")

        # Appveyor
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_PULL_REQUEST_NUMBER": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED":
                                           "more [build=missing] ",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), "missing")

        # Raise invalid
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_PULL_REQUEST_NUMBER": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED":
                                           "more [build=joujou] ",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertRaises(Exception, manager.get_commit_build_policy)

    def test_bamboo_env_vars(self):
        self.assertIsNone(os.getenv('CONAN_LOGIN_USERNAME'))

        with tools.environment_append({"bamboo_buildNumber": "xx",
                                       "bamboo_planRepository_branch": "mybranch",
                                       "bamboo_CONAN_LOGIN_USERNAME": "bamboo",
                                       "bamboo_CONAN_USER_VAR": "bamboo",
                                       "CONAN_USER_VAR": "foobar"}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch") # checks that manager is Bamboo 

            self.assertEquals(os.getenv('CONAN_LOGIN_USERNAME'), "bamboo")
            self.assertEquals(os.getenv('CONAN_USER_VAR'), "foobar")
