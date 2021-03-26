import argparse
import os
import re
from datetime import date

from github import Github


GH_TOKEN = os.getenv("GH_TOKEN")
GH_COMMIT = os.getenv("GITHUB_SHA")
REPOSITORY = os.getenv("GITHUB_REPOSITORY") or "conan-io/conan-package-tools"
TAG = "changelog:"
DOCS_TAG = "docs:"


class GHReleaser(object):
    def __init__(self, gh_token, repository):
        tmp = Github(gh_token)
        self._repo = tmp.get_repo(repository)

    def release(self, version, changelog, commit_hash, files=None):
        d = date.today()
        d_str = d.strftime("%d-%b-%Y")
        release_name = "%s (%s)" % (version, d_str)
        release = self._repo.create_git_release(version,
                                                name=release_name,
                                                message=changelog,
                                                target_commitish=commit_hash,
                                                draft=True)
        if files:
            for the_file in files:
                release.upload_asset(the_file)

        release.update_release(name=release_name,
                               message=changelog,
                               draft=False)


def get_changelog_markdown(version, repository, gh_token, with_docs=True):
    changelogs, errors = get_changelogs(repository, version, gh_token, with_docs=with_docs)
    if errors:
        raise Exception("Check the errors in the changelog and try again")

    markdown = get_markdown(changelogs)
    return markdown


def get_changelog_rst(version, repository, gh_token, docs=True):
    changelogs, errors = get_changelogs(repository, version, gh_token, with_docs=docs)
    if errors:
        raise Exception("Check the errors in the changelog and try again")

    rst = get_rst(changelogs)
    return rst


def get_rst(changelogs):
    c = order_changelogs(changelogs)
    rst = format_to_rst(c)
    return rst


def format_to_rst(changelogs):
    lines = []
    for x in changelogs:
        if x[2]: # With docs
            lines.append("- %s `#%s <%s>`_ . Docs `here <%s>`__" % (x[0],
                                                                  x[1].split("/")[-1],
                                                                  x[1],
                                                                  x[2]))
        else:
            lines.append("- %s `#%s <%s>`_" % (x[0], x[1].split("/")[-1], x[1]))
    tmp = "\n".join(lines)

    commands = ["install", "config", "get", "info", "search", "new", "create", "upload", "export",
                "export-pkg", "test", "source", "build", "package", "profile", "remote", "user",
                "imports", "copy", "remove", "alias", "download", "help", "inspect"]

    # Format detected commands with :command:
    for cmd in commands:
        regex = r"`{1,2}(conan %s)`{1,2}" % cmd
        tmp = re.sub(regex, r":command:`\1`", tmp)
    return tmp + "\n"


def print_step(message):
    print("\n\n*******************************************************************")
    print("* %s" % message)
    print("*******************************************************************\n")


def get_changelogs(repo_name, milestone, gh_token, with_docs=True):
    err = False
    changelogs = []

    g = Github(gh_token)
    repo = g.get_repo(repo_name)

    print("Searching for {} milestone".format(milestone))
    tmp = milestone.split(".")
    if len(tmp) == 3 and tmp[2] == "0":
        milestone_alternative = ".".join(tmp[0:2])
    else:
        milestone_alternative = milestone

    milestone = milestone_by_name(repo, (milestone, milestone_alternative))
    if not milestone:
        print("ERROR: Milestone not found!")
        exit(1)

    print("Reading issues from GH api...")
    issues = repo.get_issues(milestone=milestone, state="all")
    print("done!")

    for issue in issues:
        if issue.pull_request:
            body = issue.body
            if TAG in body.lower():
                tmp = _get_tag_text(TAG, body)
                if with_docs:
                    if DOCS_TAG not in body.lower():
                        print("WARNING: Empty DOCS for changelog at %s" % issue.html_url)
                        err = True
                        continue
                    docs_link = _get_tag_text(DOCS_TAG, body)
                else:
                    docs_link = None
                if docs_link:
                    if not docs_link[0].strip().startswith("https://github.com/conan-io/docs/") or docs_link[0].strip().endswith("XXX"):
                        print("WARNING: Invalid DOCS tag for changelog at %s (%s)" % (issue.html_url, docs_link))
                        err = True
                        continue
                    else:
                        pr_number = docs_link[0].rsplit('/', 1)[1]
                        docs_repo = g.get_repo("conan-io/docs")
                        docs_pr = docs_repo.get_pull(int(pr_number))
                        if not docs_pr.merged:
                            print("WARNING: Docs PR #{} is not merged.".format(pr_number))
                            err = True
                            continue
                    changelogs.extend([(cl, issue.html_url, docs_link[0]) for cl in tmp])
                else:
                    changelogs.extend([(cl, issue.html_url, None) for cl in tmp])
            else:
                print("WARNING: Empty changelog at %s" % issue.html_url)
                err = True
                continue
    return changelogs, err


def milestone_by_name(repo, milestone_names):
    milestones = list(repo.get_milestones(state="all"))
    for milestone in milestones:
        if milestone.title in milestone_names:
            return milestone
    return None


def _get_tag_text(tag, body):
    ret = []
    pos = body.lower().find(tag)
    while pos != -1:
        cl = body[pos + len(tag):].splitlines()[0]
        cl = cl.strip().strip("-")
        # Just in case "omitted" or "omit" appears in the explanation
        if cl and ("omit" not in cl.lower() or len(cl) > 20):
            ret.append(cl)
        body = body[pos + len(tag):]
        pos = body.lower().find(tag)
    return ret


def get_markdown(changelogs):
    c = order_changelogs(changelogs)
    markdown = format_to_gh(c)
    return markdown


def order_changelogs(changelogs):
    def weight(element, raising=True):
        global error
        el = element[0]
        if el.lower().startswith("feature:"):
            return 0
        elif el.lower().startswith("bugfix:"):
            return 2
        elif el.lower().startswith("fix:"):
            return 1
        else:
            msg = "WARNING: Invalid tag '%s' at %s" % (el.split(" ")[0], element[1])
            if raising:
                raise Exception("Check the errors and try again")
            else:
                print(msg)
    # To print the errors
    sorted(changelogs, key=lambda x: weight(x, raising=False))
    # To raise when errored
    return sorted(changelogs, key=lambda x: weight(x))


def format_to_gh(changelogs):
    lines = []
    for x in changelogs:
        if x[2]: # With docs
            lines.append("- %s (%s). Docs: [:page_with_curl:](%s)" % (x[0], x[1], x[2]))
        else:
            lines.append("- %s (%s)" % (x[0], x[1]))
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Launch configuration according '
                                                 'to the environment')
    parser.add_argument('--release-version', '-rv', help='CPT release version e.g: 1.8')
    parser.add_argument('--dry-run', '-d', help='Do not commit changes', action="store_true")
    args = parser.parse_args()

    release_version = args.release_version
    if release_version is None:
        github_ref = os.getenv("GITHUB_REF")
        if not github_ref:
            print("ERROR: Only Github Action supported.")
            exit(1)
        match = re.search(r"refs/tags/(.*)", github_ref)
        if not match:
            print("ERROR: Invalid branch or tag.")
            exit(1)

        release_version = match.group(1)

    # Generate changelog, verify all is ok
    print_step("Getting changelog markdown from '{}'".format(REPOSITORY, release_version))
    changelog = get_changelog_markdown(release_version, REPOSITORY, GH_TOKEN, with_docs=False)
    if not changelog:
        print("ERROR! The changelog is empty, verify the milestone name: %s" % release_version)
        exit(1)

    print(changelog)
    print("-----------------------------------")

    if args.dry_run:
        print_step("DRY RUN - SKIP Release to GitHub")
    else:
        print_step("Releasing to GitHub...")
        releaser = GHReleaser(GH_TOKEN, REPOSITORY)
        releaser.release(release_version, changelog, GH_COMMIT)
        print_step("** RELEASED **")
