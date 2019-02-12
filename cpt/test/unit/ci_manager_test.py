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
                                       "TRAVIS_BRANCH": "mybranch"
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
                                       "TRAVIS_COMMIT": "506c89117650bb12252db26d35b8c2385411f175"
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertEquals(manager.get_commit_msg(), "msg")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

        # Appveyor
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED": "more",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       "APPVEYOR_REPO_COMMIT": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertEquals(manager.get_commit_msg(), "msg more")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

        # Appveyor PULL REQUEST
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_PULL_REQUEST_NUMBER": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED": "more",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       "APPVEYOR_REPO_COMMIT": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertIsNone(manager.get_branch())
            self.assertEquals(manager.get_commit_msg(), "msg more")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

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
                                       "CIRCLE_SHA1": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

        # Gitlab
        with tools.environment_append({"GITLAB_CI": "1",
                                       "CI_BUILD_REF_NAME": "mybranch",
                                       "CI_COMMIT_TITLE": "foo bar",
                                       "CI_COMMIT_SHA": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

        # Jenkins
        with tools.environment_append({"JENKINS_URL": "1",
                                       "BRANCH_NAME": "mybranch",
                                       "GIT_COMMIT": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

        # Azure pipelines
        with tools.environment_append({"SYSTEM_TEAMFOUNDATIONCOLLECTIONURI": "https://dev.azure.com/",
                                       "BUILD_SOURCEVERSIONMESSAGE": "msg",
                                       "BUILD_SOURCEVERSION": "506c89117650bb12252db26d35b8c2385411f175",
                                       "BUILD_SOURCEBRANCHNAME": "mybranch",
                                       "BUILD_REASON": "manual",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertEquals(manager.get_commit_msg(), "msg")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")
            self.assertEquals(manager.is_pull_request(), False)

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

        # Complex messages
        m = "double travis pages again due to timeout, travis taking longer " \
            "now [skip appveyor] [build=missing]"
        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE": m}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), "missing")

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

        with tools.environment_append({"bamboo_buildNumber": "xx",
                                       "bamboo_planRepository_branch": "mybranch",
                                       "BAMBOO_CONAN_LOGIN_USERNAME": "bamboo",
                                       "BAMBOO_CONAN_USER_VAR": "bamboo",
                                       "CONAN_USER_VAR": "foobar"}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch") # checks that manager is Bamboo

            self.assertEquals(os.getenv('CONAN_LOGIN_USERNAME'), "bamboo")
            self.assertEquals(os.getenv('CONAN_USER_VAR'), "foobar")


