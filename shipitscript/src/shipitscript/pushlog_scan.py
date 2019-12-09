import logging
from enum import Enum, auto, unique

import requests

log = logging.getLogger(__name__)

URL = "https://hg.mozilla.org/{branch}/json-pushes"


@unique
class Importance(Enum):
    MAYBE = auto()
    IMPORTANT = auto()
    UNIMPORTANT = auto()


_push_checks = []


def push_check(func):
    _push_checks.append(func)
    return func


def get_shippable_revision_build(branch, last_shipped_rev, cron_rev):
    """This method queries the hg.mozilla.org server and retrieves all the commits
    that have happened between `last_shipped_rev` and the `cron_rev`. Sorted
    decreasingly over time, it iterates through them and attempts to retrieve the
    first one that is important. If none found, it'll return None and the main
    function will make the task go green.
    """
    # TODO use redo here to automatically retry
    resp = requests.get(URL.format(branch=branch), params={"full": "1", "fromchange": last_shipped_rev, "tochange": cron_rev})
    pushlog = resp.json()
    reversed_pushes = [pushlog[k] for k in sorted(pushlog.keys(), reverse=True)]
    for push in reversed_pushes:
        push_importance = is_push_important(push)
        if push_importance == Importance.IMPORTANT:
            # Tell caller that we want to build.
            return push["changesets"][-1]["node"]


def is_push_important(push):
    """
    Run through all `@push_check`s to find if this `push` is important or not.

    See the help on `Importance` for more information.
    """
    isimportant = Importance.IMPORTANT
    for check in _push_checks:
        isimportant = check(push)
        if not isimportant == Importance.MAYBE:
            return isimportant
    # We reached the end of our checks and
    # we did not explicitly detect important
    # nor unimportant.
    # ...Our default is important
    log.info(f"Could not tell the importance of the " "{push['changesets'][-1]['node']} hence defaulting to important")
    return Importance.IMPORTANT


@push_check
def skip_dontbuild(push):
    """
    Commits that contain the DONTBUILD syntax in their message"
    """
    if "DONTBUILD" in push["changesets"][-1]["desc"]:
        return Importance.UNIMPORTANT
    return Importance.MAYBE


@push_check
def is_l10n_bump(push):
    """
    L10n bumps are important.
    """
    if push["changesets"][-1]["author"] == "L10n Bumper Bot <release+l10nbumper@mozilla.com>":
        # This is the bumper bot, so important
        return Importance.IMPORTANT
    return Importance.MAYBE


@push_check
def skip_test_only(push):
    """
    Treat a=test-only (or a=testonly) as unimportant if present on the tip of a push.
    """
    # get the tip
    cset = push["changesets"][-1]
    if "a=test-only" in cset["desc"] or "a=testonly" in cset["desc"]:
        return Importance.UNIMPORTANT
    return Importance.MAYBE


@push_check
def skip_version_bump(push):
    """
    Do not treat version bumps as important to determine if we should build.
    """
    cset = push["changesets"][-1]
    if push["changesets"][-1]["author"] == "Mozilla Releng Treescript <release+treescript@mozilla.org>":
        if "Automatic version bump" in cset["desc"]:
            # This is a version bump
            return Importance.UNIMPORTANT
    # Anything else may still be important
    return Importance.MAYBE
