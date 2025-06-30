import logging
import os
from enum import IntEnum, auto, unique

import requests

log = logging.getLogger(__name__)

URL = "https://hg.mozilla.org/{branch}/json-pushes"
GITHUB_URL = "https://api.github.com/repos/{owner}/{repository_name}/compare/{base}...{compare}"


@unique
class Importance(IntEnum):
    MAYBE = auto()
    UNIMPORTANT = auto()
    IMPORTANT = auto()
    SKIP = auto()


_push_checks_hg = []


def push_check_hg(func):
    _push_checks_hg.append(func)
    return func


def get_shippable_revision_build(branch, last_shipped_rev, cron_rev, parsed_repository_url):
    if parsed_repository_url is not None and parsed_repository_url.platform == "github":
        return _get_shippable_revision_build_github(parsed_repository_url, last_shipped_rev, cron_rev)

    return _get_shippable_revision_build_hg(branch, last_shipped_rev, cron_rev)


def _get_shippable_revision_build_hg(branch, last_shipped_rev, cron_rev):
    """This method queries the hg.mozilla.org server and retrieves all the commits
    that have happened between `last_shipped_rev` and the `cron_rev`. Sorted
    decreasingly over time, it iterates through them and attempts to retrieve the
    first one that is important. If none found, it'll return None and the main
    function will make the task go green.
    """
    # TODO use redo here to automatically retry
    resp = requests.get(URL.format(branch=branch), params={"full": "1", "fromchange": last_shipped_rev, "tochange": cron_rev})
    pushlog = resp.json()
    # we strip out all the pushes that contain other branches' commits (e.g. relbranch)
    reversed_pushes = [pushlog[k] for k in sorted(pushlog.keys(), reverse=True) if pushlog[k]["changesets"][0]["branch"] == "default"]
    for push in reversed_pushes:
        push_importance = is_push_important_hg(push)
        if push_importance == Importance.IMPORTANT:
            # Tell caller that we want to build.
            return push["changesets"][-1]["node"]
        if push_importance == Importance.SKIP:
            # Tell caller that we do not want to build.
            return None


def _get_shippable_revision_build_github(parsed_repository_url, last_shipped_rev, cron_rev):
    headers = {
        "User-Agent": "shipitscript",
    }

    if "GITHUB_TOKEN" in os.environ:
        headers["Authorization"] = "Bearer {}".format(os.environ["GITHUB_TOKEN"])

    resp = requests.get(
        GITHUB_URL.format(owner=parsed_repository_url.owner, repository_name=parsed_repository_url.repo, base=last_shipped_rev, compare=cron_rev),
        headers=headers,
    )
    resp.raise_for_status()

    pushlog = resp.json()["commits"]

    for commit in reversed(pushlog):
        if is_commit_important_github(commit["commit"]):
            return commit["sha"]

    return None


def is_commit_important_github(commit):
    if "DONTBUILD" in commit["message"]:
        return False

    if commit["author"]["name"].startswith("releng-treescript"):
        return False

    return True


def is_push_important_hg(push):
    """
    Run through all `@push_check_hg`s to find if this `push` is important or not.

    See the help on `Importance` for more information.
    """
    isimportant = Importance.MAYBE
    for check in _push_checks_hg:
        isimportant = max(isimportant, check(push))
    if not isimportant == Importance.MAYBE:
        return isimportant
    # We reached the end of our checks and
    # we did not explicitly detect important
    # nor unimportant.
    # ...Our default is important
    log.info(f"Could not tell the importance of {push['changesets'][-1]['node']}, hence defaulting to IMPORTANT")
    return Importance.IMPORTANT


@push_check_hg
def skip_dontbuild(push):
    """
    Commits that contain the DONTBUILD syntax in their message"
    """
    if "DONTBUILD" in push["changesets"][-1]["desc"]:
        return Importance.UNIMPORTANT
    return Importance.MAYBE


@push_check_hg
def is_l10n_bump(push):
    """
    L10n bumps are important.
    """
    if push["changesets"][-1]["author"] == "L10n Bumper Bot <release+l10nbumper@mozilla.com>":
        # This is the bumper bot, so important
        return Importance.IMPORTANT
    return Importance.MAYBE


@push_check_hg
def skip_test_only(push):
    """
    Treat a=test-only (or a=testonly) as unimportant if present on every changeset in a push.
    """
    # XXX: 25 is a number with no specific meaning. It's just a performance break
    # in case we need to loop through very large pushlogs, such as mergeduty,
    # in which case we can assume by default that the revision is IMPORTANT
    if len(push["changesets"]) > 25:
        return Importance.IMPORTANT

    for commit in push["changesets"]:
        if "a=test-only" not in commit["desc"] and "a=testonly" not in commit["desc"]:
            # at least one commit in the push is non-testonly, hence potentially important
            return Importance.MAYBE
    return Importance.UNIMPORTANT


@push_check_hg
def skip_version_bump(push):
    """
    Do not treat version bumps as important to determine if we should build.
    """
    cset = push["changesets"][-1]
    if push["changesets"][-1]["author"] == "Mozilla Releng Treescript <release+treescript@mozilla.org>":
        if "Automatic version bump" in cset["desc"]:
            # This is a version bump; earlier pushes have the wrong version number, so we need to stop looking
            return Importance.SKIP
    # Anything else may still be important
    return Importance.MAYBE
