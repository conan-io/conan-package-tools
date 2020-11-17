import unittest
import os

from cpt.test.utils.tools import TestBufferConanOutput
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

    def test_bamboo_instance(self):
        with tools.environment_append({"bamboo_buildNumber": "xx",
                                       "bamboo_planRepository_branch": "mybranch"}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())

    def test_travis_instance(self):
        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE": "msg",
                                       "TRAVIS_BRANCH": "mybranch",
                                       "TRAVIS_COMMIT": "506c89117650bb12252db26d35b8c2385411f175"
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertEquals(manager.get_commit_msg(), "msg")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

    def test_appveyor_instance(self):
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

    def test_circleci_instance(self):
        with tools.environment_append({"CIRCLECI": "1",
                                       "CIRCLE_BRANCH": "mybranch",
                                       "CIRCLE_SHA1": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")
            self.assertEquals(manager.is_pull_request(), False)

        with tools.environment_append({"CIRCLECI": "1",
                                       "CIRCLE_BRANCH": "pull/35",
                                       "CIRCLE_SHA1": "506c89117650bb12252db26d35b8c2385411f175",
                                       "CIRCLE_PULL_REQUEST": "https://github.com/org/repo/pull/35"
                                       }):
            manager = CIManager(self.printer)
            self.assertIsNone(manager.get_branch())
            self.assertIsNotNone(manager.get_commit_msg())
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")
            self.assertEquals(manager.is_pull_request(), True)

    def test_gitlab_instance(self):
        with tools.environment_append({"GITLAB_CI": "1",
                                       "CI_BUILD_REF_NAME": "mybranch",
                                       "CI_COMMIT_TITLE": "foo bar",
                                       "CI_COMMIT_SHA": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

    def test_jenkins_instance(self):
        with tools.environment_append({"JENKINS_URL": "1",
                                       "BRANCH_NAME": "mybranch",
                                       "GIT_COMMIT": "506c89117650bb12252db26d35b8c2385411f175",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertIsNotNone(manager.get_commit_msg())
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")

    def test_azure_instance(self):
        with tools.environment_append({"SYSTEM_TEAMFOUNDATIONCOLLECTIONURI": "https://dev.azure.com/",
                                       "BUILD_SOURCEVERSIONMESSAGE": "msg",
                                       "BUILD_SOURCEVERSION": "506c89117650bb12252db26d35b8c2385411f175",
                                       "BUILD_SOURCEBRANCH": "mybranch",
                                       "BUILD_REASON": "manual",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "mybranch")
            self.assertEquals(manager.get_commit_msg(), "msg")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")
            self.assertEquals(manager.is_pull_request(), False)

        with tools.environment_append({"SYSTEM_TEAMFOUNDATIONCOLLECTIONURI": "https://dev.azure.com/",
                                       "BUILD_SOURCEVERSIONMESSAGE": "msg",
                                       "BUILD_SOURCEVERSION": "506c89117650bb12252db26d35b8c2385411f175",
                                       "BUILD_SOURCEBRANCH": "refs/heads/testing/version",
                                       "BUILD_REASON": "PullRequest",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "testing/version")
            self.assertEquals(manager.get_commit_msg(), "msg")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")
            self.assertEquals(manager.is_pull_request(), True)

        with tools.environment_append({"SYSTEM_TEAMFOUNDATIONCOLLECTIONURI": "https://dev.azure.com/",
                                       "BUILD_SOURCEVERSIONMESSAGE": "msg",
                                       "BUILD_SOURCEVERSION": "506c89117650bb12252db26d35b8c2385411f175",
                                       "BUILD_SOURCEBRANCH": "refs/heads/stable/version",
                                       "BUILD_REASON": "IndividualCI",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "stable/version")
            self.assertEquals(manager.get_commit_msg(), "msg")
            self.assertEquals(manager.get_commit_id(), "506c89117650bb12252db26d35b8c2385411f175")
            self.assertEquals(manager.is_pull_request(), False)

    def test_shippable_instance(self):
        shippable_env = {   "SHIPPABLE": "true",
                            "COMMIT_MESSAGE": "foobar [qux]",
                            "COMMIT": "98e984eacf4e3dfea431c8850c8c181a08e8cf3d",
                            "BRANCH": "testing/5.6.5",
                            "IS_GIT_TAG": "false",
                            "IS_PULL_REQUEST": "false"}
        with tools.environment_append(shippable_env):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), shippable_env["BRANCH"])
            self.assertEquals(manager.get_commit_msg(), shippable_env["COMMIT_MESSAGE"])
            self.assertEquals(manager.get_commit_id(), shippable_env["COMMIT"])
            self.assertEquals(manager.is_pull_request(), False)
            self.assertEquals(manager.is_tag(), False)

        shippable_env = {   "SHIPPABLE": "true",
                            "COMMIT_MESSAGE": "new tag",
                            "COMMIT": "98e984eacf4e3dfea431c8850c8c181a08e8cf3d",
                            "BRANCH": "release/5.6.5",
                            "IS_GIT_TAG": "true",
                            "IS_PULL_REQUEST": "true"}
        with tools.environment_append(shippable_env):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), shippable_env["BRANCH"])
            self.assertEquals(manager.get_commit_msg(), shippable_env["COMMIT_MESSAGE"])
            self.assertEquals(manager.get_commit_id(), shippable_env["COMMIT"])
            self.assertEquals(manager.is_pull_request(), True)
            self.assertEquals(manager.is_tag(), True)

    def test_github_actions_instance(self):
        gha_env = {"GITHUB_ACTIONS": "true",
                   "GITHUB_SHA": "98e984eacf4e3dfea431c8850c8c181a08e8cf3d",
                   "GITHUB_REF": "testing/5.6.5",
                   "GITHUB_BASE_REF": "testing/5.6.5",
                   "GITHUB_EVENT_NAME": "push"}
        with tools.environment_append(gha_env):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), gha_env["GITHUB_REF"])
            self.assertEquals(manager.get_commit_id(), gha_env["GITHUB_SHA"])
            self.assertEquals(manager.is_pull_request(), False)

        gha_env = {"GITHUB_ACTIONS": "true",
                   "GITHUB_SHA": "98e984eacf4e3dfea431c8850c8c181a08e8cf3d",
                   "GITHUB_REF": "quick_fix",
                   "GITHUB_BASE_REF": "testing/5.6.5",
                   "GITHUB_EVENT_NAME": "pull_request"}
        with tools.environment_append(gha_env):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), gha_env["GITHUB_BASE_REF"])
            self.assertEquals(manager.get_commit_id(), gha_env["GITHUB_SHA"])
            self.assertEquals(manager.is_pull_request(), True)

        gha_env = {"GITHUB_ACTIONS": "true",
                   "GITHUB_REF": "refs/heads/testing",
                   "GITHUB_EVENT_NAME": "push"}
        with tools.environment_append(gha_env):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_branch(), "testing")

    def test_build_policy(self):
        # Travis
        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE":
                                           "This is a great commit [build=outdated] End."}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), ["outdated"])
            self.assertEquals(manager.get_commit_msg(), "This is a great commit "
                                                        "[build=outdated] End.")

        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE":
                                           "This is a great commit [build=all] End."}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), ["all"])
            self.assertEquals(manager.get_commit_msg(), "This is a great commit "
                                                        "[build=all] End.")
        # Appveyor
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_PULL_REQUEST_NUMBER": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED":
                                           "more [build=missing] ",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), ["missing"])

        # Complex messages
        m = "double travis pages again due to timeout, travis taking longer " \
            "now [skip appveyor] [build=missing]"
        with tools.environment_append({"TRAVIS": "1",
                                       "TRAVIS_COMMIT_MESSAGE": m}):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), ["missing"])

        # multiple build policies
        with tools.environment_append({"APPVEYOR": "1",
                                       "APPVEYOR_PULL_REQUEST_NUMBER": "1",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE": "msg",
                                       "APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED":
                                           "more [build=missing] [build=pattern] ",
                                       "APPVEYOR_REPO_BRANCH": "mybranch",
                                       }):
            manager = CIManager(self.printer)
            self.assertEquals(manager.get_commit_build_policy(), ["missing", "pattern"])

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
