import re
import os
import subprocess


def is_travis():
    return os.getenv("TRAVIS", False)


def is_appveyor():
    return os.getenv("APPVEYOR", False)


def is_bamboo():
    return os.getenv("bamboo_buildNumber", False)


def is_jenkins():
    return os.getenv("JENKINS_URL", False)


def is_gitlab():
    return os.getenv("GITLAB_CI", False)


def is_circle_ci():
    return os.getenv("CIRCLECI", False)


def is_azure_pipelines():
    return os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI", False)


def is_shippable():
    return os.getenv("SHIPPABLE", False)


def is_github_actions():
    return os.getenv("GITHUB_ACTIONS", False)


class CIManager(object):
    def __init__(self, printer):

        self.manager = None
        self.printer = printer
        if is_travis():
            self.manager = TravisManager(printer)
        elif is_appveyor():
            self.manager = AppveyorManager(printer)
        elif is_bamboo():
            self.manager = BambooManager(printer)
        elif is_circle_ci():
            self.manager = CircleCiManager(printer)
        elif is_gitlab():
            self.manager = GitlabManager(printer)
        elif is_jenkins():
            self.manager = JenkinsManager(printer)
        elif is_azure_pipelines():
            self.manager = AzurePipelinesManager(printer)
        elif is_shippable():
            self.manager = ShippableManager(printer)
        elif is_github_actions():
            self.manager = GitHubActionsManager(printer)
        else:
            self.manager = GenericManager(printer)

    def get_commit_build_policy(self):
        msg = self.get_commit_msg()
        if not msg:
            return None
        pattern = "\[build=(\w*)\]"
        prog = re.compile(pattern)
        matches = prog.findall(msg)
        if matches:
            build_policy = matches
            return build_policy
        return None


    def skip_builds(self):
        if os.getenv("CONAN_IGNORE_SKIP_CI"):
            return False
        pattern = "^.*\[skip ci\].*$"
        prog = re.compile(pattern)
        msg = self.get_commit_msg()
        if not msg:
            return False
        return prog.match(msg)

    def get_branch(self):
        return self.manager.get_branch()

    def get_commit_msg(self):
        return self.manager.get_commit_msg()

    def is_pull_request(self):
        return self.manager.is_pull_request()

    def is_tag(self):
        return self.manager.is_tag()

    def get_commit_id(self):
        return self.manager.get_commit_id()


class GenericManager(object):
    def __init__(self, printer):
        self.printer = printer

    def get_commit_msg(self):
        try:
            msg = subprocess.check_output("git log -1 --format=%s%n%b", shell=True).decode().strip()
            return msg
        except Exception:
            pass

    def get_commit_id(self):
        try:
            msg = subprocess.check_output("git rev-parse HEAD", shell=True).decode().strip()
            return msg
        except Exception:
            pass

    def get_branch(self):
        try:
            for line in subprocess.check_output("git branch", shell=True).decode().splitlines():
                line = line.strip()
                if line.startswith("*") and " (HEAD detached" not in line:
                    return line.replace("*", "", 1).strip()
            return None
        except Exception:
            pass

        return None

    def is_pull_request(self):
        return None

    def is_tag(self):
        try:
            return True if \
                subprocess.check_output("git tag -l --points-at HEAD",
                                        shell=True).decode().splitlines() else False
        except Exception:
            pass
        return False


class TravisManager(GenericManager):
    def __init__(self, printer):
        super(TravisManager, self).__init__(printer)
        self.printer.print_message("- CI detected: Travis CI")

    def get_commit_msg(self):
        return os.getenv("TRAVIS_COMMIT_MESSAGE", None)

    def get_commit_id(self):
        return os.getenv("TRAVIS_COMMIT", None)

    def get_branch(self):
        return os.getenv("TRAVIS_BRANCH", None)

    def is_pull_request(self):
        return os.getenv("TRAVIS_PULL_REQUEST", "false") != "false"

    def is_tag(self):
        return os.getenv("TRAVIS_TAG", None)


class AppveyorManager(GenericManager):
    def __init__(self, printer):
        super(AppveyorManager, self).__init__(printer)
        self.printer.print_message("- CI detected: Appveyor")

    def get_commit_msg(self):
        commit = os.getenv("APPVEYOR_REPO_COMMIT_MESSAGE", None)
        if commit:
            extended = os.getenv("APPVEYOR_REPO_COMMIT_MESSAGE_EXTENDED", None)
            if extended:
                return commit + " " + extended
        return commit

    def get_commit_id(self):
        return os.getenv("APPVEYOR_REPO_COMMIT", None)

    def get_branch(self):
        if self.is_pull_request():
            return None

        return os.getenv("APPVEYOR_REPO_BRANCH", None)

    def is_pull_request(self):
        return os.getenv("APPVEYOR_PULL_REQUEST_NUMBER", None)

    def is_tag(self):
        return os.getenv("APPVEYOR_REPO_TAG", "false") != "false"


class BambooManager(GenericManager):
    def __init__(self, printer):
        super(BambooManager, self).__init__(printer)
        self.printer.print_message("CI detected: Bamboo")

        for var in list(os.environ.keys()):
            result = re.match('\A[bB][aA][mM][bB][oO][oO]_(CONAN.*)', var)
            if result != None and os.getenv(result.group(1), None) == None:
                self.printer.print_message("de-bambooized CONAN env var : %s " % result.group(1))
                os.environ[result.group(1)] = os.environ[var]

    def get_branch(self):
        return os.getenv("bamboo_planRepository_branch", None)


class CircleCiManager(GenericManager):
    def __init__(self, printer):
        super(CircleCiManager, self).__init__(printer)
        self.printer.print_message("CI detected: Circle CI")

    def get_commit_id(self):
        return os.getenv("CIRCLE_SHA1", None)

    def get_branch(self):
        if self.is_pull_request():
            return None
        return os.getenv("CIRCLE_BRANCH", None)

    def is_pull_request(self):
        return "CIRCLE_PULL_REQUEST" in os.environ

    def is_tag(self):
        return os.getenv("CIRCLE_TAG", None)


class GitlabManager(GenericManager):
    def __init__(self, printer):
        super(GitlabManager, self).__init__(printer)
        self.printer.print_message("CI detected: Gitlab")

    def get_commit_msg(self):
        return os.getenv("CI_COMMIT_TITLE", None)

    def get_commit_id(self):
        return os.getenv("CI_COMMIT_SHA", None)

    def get_branch(self):
        return os.getenv("CI_BUILD_REF_NAME", None)

    def is_pull_request(self):
        return os.getenv("CI_MERGE_REQUEST_ID", None)

    def is_tag(self):
        return os.getenv("CI_COMMIT_TAG", None)


class JenkinsManager(GenericManager):
    def __init__(self, printer):
        super(JenkinsManager, self).__init__(printer)
        self.printer.print_message("CI detected: Jenkins")

    def get_commit_id(self):
        return os.getenv("GIT_COMMIT", None)

    def get_branch(self):
        return os.getenv("BRANCH_NAME", None)


class AzurePipelinesManager(GenericManager):
    def __init__(self, printer):
        super(AzurePipelinesManager, self).__init__(printer)
        self.printer.print_message("CI detected: Azure Pipelines")

    def get_commit_msg(self):
        return os.getenv("BUILD_SOURCEVERSIONMESSAGE", None)

    def get_commit_id(self):
        return os.getenv("BUILD_SOURCEVERSION", None)

    def get_branch(self):
        branch = os.getenv("BUILD_SOURCEBRANCH", None)
        if branch.startswith("refs/heads/"):
            branch = branch[11:]
        return branch

    def is_pull_request(self):
        return os.getenv("BUILD_REASON", "false") == "PullRequest"


class GitHubActionsManager(GenericManager):
    def __init__(self, printer):
        super(GitHubActionsManager, self).__init__(printer)
        self.printer.print_message("CI detected: GitHub Actions")

    def get_commit_msg(self):
        try:
            msg = subprocess.check_output("git log -1 --format=%s%n%b {}".format(self.get_commit_id()),
                                          shell=True).decode().strip()
            return msg
        except Exception:
            return None

    def get_commit_id(self):
        return os.getenv("GITHUB_SHA", None)

    def get_branch(self):
        branch = os.getenv("GITHUB_REF", None)
        if self.is_pull_request():
            branch = os.getenv("GITHUB_BASE_REF", "")
        if branch.startswith("refs/heads/"):
            branch = branch[11:]
        return branch

    def is_pull_request(self):
        return os.getenv("GITHUB_EVENT_NAME", "") == "pull_request"


class ShippableManager(GenericManager):

    def __init__(self, printer):
        super(ShippableManager, self).__init__(printer)
        self.printer.print_message("CI detected: Shippable")

    def get_commit_msg(self):
        return os.getenv("COMMIT_MESSAGE", None)

    def get_commit_id(self):
        return os.getenv("COMMIT", None)

    def get_branch(self):
        return os.getenv("BRANCH", None)

    def is_pull_request(self):
        return os.getenv("IS_PULL_REQUEST", None) == "true"

    def is_tag(self):
        return os.getenv("IS_GIT_TAG", None) == "true"
