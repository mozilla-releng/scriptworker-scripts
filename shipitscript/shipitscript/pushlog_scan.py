from enum import Enum, auto, unique

import requests

URL = 'https://hg.mozilla.org/{repo}/json-pushes'


@unique
class Importance(Enum):
    MAYBE = auto()
    IMPORTANT = auto()
    UNIMPORTANT = auto()


_push_checks = []


def push_check(func):
    _push_checks.append(func)
    return func


def should_build(repo, old_rev, curr_rev):
    # TODO redo
    resp = requests.get(
        URL.format(repo=repo),
        params={'full': '1', 'fromchange': old_rev, 'tochange': curr_rev},
    )
    pushlog = resp.json()
    reversed_pushes = [pushlog[k] for k in sorted(pushlog.keys(), reverse=True)]
    for push in reversed_pushes:
        push_importance = is_push_important(push)
        if push_importance == Importance.IMPORTANT:
            # Tell caller that we want to build.
            return True
    return False


def is_push_important(push):
    """
    Run through all `@push_check`s to find if this `push` is important or not.

    See the help on `Importance` for more information.
    """
    isimportant = Importance.MAYBE
    for check in _push_checks:
        isimportant = check(push)
        if not isimportant == Importance.MAYBE:
            return isimportant
    # We reached the end of our checks and
    # we did not explicitly detect important
    # nor unimportant.
    # ...Our default is important
    return Importance.IMPORTANT


@push_check
def is_l10n_bump(push):
    """
    L10n bumps are important.
    """
    if not push['user'] == 'ffxbld':
        # Not a ffxbld user, but might still be important
        return Importance.MAYBE
    cset = push['changesets'][-1]
    if cset['author'] == 'L10n Bumper Bot <release+l10nbumper@mozilla.com>':
        # This is the bumper bot, so important
        return Importance.IMPORTANT
    # Anything else may still be important
    return Importance.MAYBE


@push_check
def skip_test_only(push):
    """
    Treat a=test-only (or a=testonly) as unimportant if present on the tip of a push.
    """
    # Get the tip
    cset = push['changesets'][-1]
    if 'a=test-only' in cset['desc'] or 'a=testonly' in cset['desc']:
        return Importance.UNIMPORTANT


@push_check
def skip_version_bump(push):
    """
    Do not treat version bumps as important to determine if we should build.
    """
    if not push['user'] == 'ffxbld':
        # Not a ffxbld user, but might still be important
        return Importance.MAYBE
    cset = push['changesets'][-1]
    if cset['author'] == 'Mozilla Releng Treescript <release+treescript@mozilla.org>':
        if 'Automatic version bump' in cset['desc']:
            # This is a version bump
            return Importance.UNIMPORTANT
    # Anything else may still be important
    return Importance.MAYBE
