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
        else:
            self.manager = GenericManager(printer)

    def get_commit_build_policy(self):
        pattern = "^.*\[build=(\w*)\].*$"
        prog = re.compile(pattern)
        msg = self.get_commit_msg()
        if not msg:
            return None
        matches = prog.match(msg)
        if matches:
            build_policy = matches.groups()[0]
            if build_policy not in ("never", "outdated", "missing"):
                raise Exception("Invalid build policy, valid values: never, outdated, missing")
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


class GenericManager(object):
    def __init__(self, printer):
        self.printer = printer

    def get_commit_msg(self):
        try:
            msg = subprocess.check_output("git log -1 --format=%s%n%b", shell=True).decode().strip()
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
            result = re.match('\Abamboo_(CONAN.*)', var)
            if result != None and os.getenv(result.group(1), None) == None:
                self.printer.print_message("de-bambooized CONAN env var : %s " % result.group(1))
                os.environ[result.group(1)] = os.environ[var]

    def get_branch(self):
        return os.getenv("bamboo_planRepository_branch", None)


class CircleCiManager(GenericManager):
    def __init__(self, printer):
        super(CircleCiManager, self).__init__(printer)
        self.printer.print_message("CI detected: Circle CI")

    def get_branch(self):
        return os.getenv("CIRCLE_BRANCH", None)

    def is_pull_request(self):
        return os.getenv("CIRCLE_PULL_REQUEST", None)

    def is_tag(self):
        return os.getenv("CIRCLE_TAG", None)


class GitlabManager(GenericManager):
    def __init__(self, printer):
        super(GitlabManager, self).__init__(printer)
        self.printer.print_message("CI detected: Gitlab")

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

    def get_branch(self):
        return os.getenv("BRANCH_NAME", None)
