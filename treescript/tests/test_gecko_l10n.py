import json
import os

import pytest
from scriptworker_client.utils import makedirs
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from treescript.exceptions import TaskVerificationError, TreeScriptError

import treescript.gecko.l10n as l10n

try:
    from unittest.mock import AsyncMock
except ImportError:
    # TODO: Remove this import once py3.7 is not supported anymore
    from mock import AsyncMock


async def noop_async(*args, **kwargs):
    pass


# build_locale_map {{{1
def test_build_locale_map():
    """build_locale_map returns a set of changes between old_contents
    and new_contents.

    """
    my_platforms = ["platform1", "platform2"]
    my_rev = "my_revision"
    my_dict = {"platforms": my_platforms, "revision": my_rev}
    old_contents = {
        "existing_different_rev": {"revision": "different_rev", "platforms": my_platforms},
        "duplicate": my_dict,
        "existing_different_platforms": {"revision": my_rev, "platforms": ["different", "platforms"]},
        "existing_different_both": {"revision": "different_rev", "platforms": ["different", "platforms"]},
        "old": {"revision": "different_rev", "platforms": my_platforms},
    }
    new_contents = {
        "existing_different_rev": my_dict,
        "duplicate": my_dict,
        "existing_different_platforms": my_dict,
        "existing_different_both": my_dict,
        "new": my_dict,
    }
    expected = {
        "existing_different_rev": my_rev,
        "existing_different_platforms": my_platforms,
        "existing_different_both": my_rev,
        "old": "removed",
        "new": my_rev,
    }
    assert l10n.build_locale_map(old_contents, new_contents) == expected


# build_platform_dict {{{1
@pytest.mark.parametrize(
    "contents, bump_config, expected",
    (
        (
            [
                """one
two
three
four
en-US
five
six
""",
                """one
three
five
""",
            ],
            {
                "platform_configs": [
                    {"platforms": ["android-api-16", "android"], "path": "mobile/android/locales/all-locales"},
                    {"platforms": ["android-multilocale"], "path": "mobile/android/locales/maemo-locales"},
                ]
            },
            {
                "one": {"platforms": ["android", "android-api-16", "android-multilocale"]},
                "two": {"platforms": ["android", "android-api-16"]},
                "three": {"platforms": ["android", "android-api-16", "android-multilocale"]},
                "four": {"platforms": ["android", "android-api-16"]},
                "five": {"platforms": ["android", "android-api-16", "android-multilocale"]},
                "six": {"platforms": ["android", "android-api-16"]},
            },
        ),
        (
            [
                """one x
two y
en-US
three z
ja a
ja-JP-mac b
"""
            ],
            {
                "ignore_config": {"ja": ["macosx64", "macosx64-devedition"], "ja-JP-mac": ["linux", "linux-devedition", "linux64", "linux64-devedition"]},
                "platform_configs": [
                    {
                        "platforms": ["linux", "linux-devedition", "linux64", "linux64-devedition", "macosx64", "macosx64-devedition"],
                        "path": "browser/locales/shipped-locales",
                        "format": "shipped-locales",
                    }
                ],
            },
            {
                "one": {"platforms": ["linux", "linux-devedition", "linux64", "linux64-devedition", "macosx64", "macosx64-devedition"]},
                "two": {"platforms": ["linux", "linux-devedition", "linux64", "linux64-devedition", "macosx64", "macosx64-devedition"]},
                "three": {"platforms": ["linux", "linux-devedition", "linux64", "linux64-devedition", "macosx64", "macosx64-devedition"]},
                "ja": {"platforms": ["linux", "linux-devedition", "linux64", "linux64-devedition"]},
                "ja-JP-mac": {"platforms": ["macosx64", "macosx64-devedition"]},
            },
        ),
    ),
)
def test_build_platform_dict(contents, mocker, bump_config, expected, tmpdir):
    """build_platform_dict builds a list of platforms per locale, given
    the ignore_config and platform_configs in the l10n_bump_config.

    """
    for pc in bump_config["platform_configs"]:
        path = os.path.join(tmpdir, pc["path"])
        makedirs(os.path.dirname(path))
        with open(path, "w") as fh:
            fh.write(contents.pop(0))

    assert l10n.build_platform_dict(bump_config, tmpdir) == expected


# get_latest_revision {{{1
@pytest.mark.asyncio
async def test_get_latest_revision(mocker):
    """get_latest_revision downloads and parses the hgpushlog for a locale
    and returns the (locale, latest_revision).

    """
    expected = ("LOC", "REV")
    pushlog = {
        "lastpushid": "12345",
        "pushes": {"12344": {}, "12345": {"changesets": ["REV"]}},
    }

    async def fake_download(url, path):
        with open(path, "w") as fh:
            fh.write(json.dumps(pushlog))

    mocker.patch.object(l10n, "download_file", new=fake_download)
    assert await l10n.get_latest_revision("LOC", "") == expected


# build_revision_dict {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "old_contents, expected",
    (
        (
            {
                "one": {"pin": True, "revision": "one_orig_revision"},
                "two": {"pin": False, "revision": "two_orig_revision"},
                "three": {"revision": "three_orig_revision"},
            },
            {
                "one": {"pin": True, "revision": "one_orig_revision", "platforms": ["platform"]},
                "two": {"pin": False, "revision": "two_new_revision", "platforms": ["platform"]},
                "three": {"pin": False, "revision": "three_new_revision", "platforms": ["platform"]},
            },
        ),
        (
            None,
            {
                "one": {"revision": "default", "platforms": ["platform"]},
                "two": {"revision": "default", "platforms": ["platform"]},
                "three": {"revision": "default", "platforms": ["platform"]},
            },
        ),
    ),
)
async def test_build_revision_dict(mocker, old_contents, expected):
    """``build_revision_dict`` polls hg pushlog for latest revision information,
    unless pinned; otherwise it adds l10n dashboard revisions, if available,
    to the platform_dict; otherwise it adds a revision of "default" to
    every locale in the platform_dict.

    """
    platform_dict = {"one": {"platforms": ["platform"]}, "two": {"platforms": ["platform"]}, "three": {"platforms": ["platform"]}}
    bump_config = {}
    if old_contents:
        bump_config["l10n_repo_url"] = "x"

    def build_platform_dict(*args):
        return platform_dict

    async def get_latest_revision(locale, url):
        return (locale, f"{locale}_new_revision")

    mocker.patch.object(l10n, "build_platform_dict", new=build_platform_dict)
    mocker.patch.object(l10n, "get_latest_revision", new=get_latest_revision)
    assert await l10n.build_revision_dict(bump_config, "", old_contents) == expected


# build_revision_dict_github {{{1
@pytest.mark.asyncio
async def test_build_revision_dict_github(mocker, aioresponses, github_client):
    platform_dict = {"one": {"platforms": ["platform"]}, "two": {"platforms": ["platform"]}, "three": {"platforms": ["platform"]}}
    bump_config = {"l10n_repo_target_branch": "branchy"}

    def build_platform_dict(*args):
        return platform_dict

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"object": {"oid": "new_revision"}}}})

    mocker.patch.object(l10n, "build_platform_dict", new=build_platform_dict)
    got = await l10n.build_revision_dict_github(github_client, bump_config, "")
    assert got == {
        "one": {"pin": False, "revision": "new_revision", "platforms": ["platform"]},
        "two": {"pin": False, "revision": "new_revision", "platforms": ["platform"]},
        "three": {"pin": False, "revision": "new_revision", "platforms": ["platform"]},
    }


@pytest.mark.asyncio
async def test_build_revision_dict_github_branch_not_in_config(mocker):
    platform_dict = {"one": {"platforms": ["platform"]}, "two": {"platforms": ["platform"]}, "three": {"platforms": ["platform"]}}
    bump_config = {}

    try:
        await l10n.build_revision_dict_github({}, bump_config, "")
    except TaskVerificationError as e:
        assert str(e) == "l10n_repo_target_branch must be present in bump_config!"
        return

    assert False, "Should've raised TaskVerificationError"


@pytest.mark.asyncio
async def test_build_revision_dict_github_branch_not_in_repo(mocker, aioresponses, github_client):
    platform_dict = {"one": {"platforms": ["platform"]}, "two": {"platforms": ["platform"]}, "three": {"platforms": ["platform"]}}
    bump_config = {"l10n_repo_target_branch": "branchy"}

    def build_platform_dict(*args):
        return platform_dict

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"ref": None}}})

    mocker.patch.object(l10n, "build_platform_dict", new=build_platform_dict)

    with pytest.raises(TreeScriptError, match="branch 'branchy' not found in repo!"):
        await l10n.build_revision_dict_github(github_client, bump_config, "")


# build_commit_message {{{1
@pytest.mark.parametrize("dontbuild, ignore_closed_tree", ((True, True), (False, False)))
def test_build_commit_message(dontbuild, ignore_closed_tree):
    """build_commit_message adds the correct approval strings and a comment
    including the changes landed.
    """
    locale_map = {"a": "arev", "b": "brev", "c": "crev", "old": "removed", "p": ["platform"]}
    expected = ["no bug - Bumping foo r=release a=l10n-bump", "", "a -> arev", "b -> brev", "c -> crev", "old -> removed", "p -> ['platform']"]
    if dontbuild:
        expected[0] += l10n.DONTBUILD_MSG
    if ignore_closed_tree:
        expected[0] += l10n.CLOSED_TREE_MSG
    assert l10n.build_commit_message("foo", locale_map, dontbuild=dontbuild, ignore_closed_tree=ignore_closed_tree).splitlines() == expected


# l10n_bump {{{1
@pytest.mark.parametrize(
    "ignore_closed_tree, l10n_bump_info, old_contents, new_contents, changes",
    (
        (
            True,
            [{"name": "x", "path": "x"}],
            {"one": {"revision": "onerev", "platforms": ["platform"]}, "two": {"revision": "tworev", "platforms": ["platform"]}},
            {"one": {"revision": "onerev", "platforms": ["platform"]}, "two": {"revision": "tworev", "platforms": ["platform"]}},
            0,
        ),
        (
            False,
            [{"name": "x", "path": "x", "l10n_repo_url": "x"}, {"name": "y", "path": "y"}],
            {"one": {"revision": "oldonerev", "platforms": ["platform"]}, "two": {"revision": "oldtworev", "platforms": ["platform"]}},
            {"one": {"revision": "newonerev", "platforms": ["platform"]}, "two": {"revision": "newtworev", "platforms": ["platform"]}},
            2,
        ),
    ),
)
@pytest.mark.asyncio
async def test_l10n_bump(mocker, ignore_closed_tree, l10n_bump_info, tmpdir, old_contents, new_contents, changes):
    """l10n_bump flow coverage."""

    async def check_treestatus(*args):
        return True

    async def fake_build_revision_dict(*args, **kwargs):
        return new_contents

    mocker.patch.object(l10n, "get_dontbuild", return_value=False)
    mocker.patch.object(l10n, "get_ignore_closed_tree", return_value=ignore_closed_tree)
    mocker.patch.object(l10n, "check_treestatus", new=check_treestatus)
    mocker.patch.object(l10n, "get_l10n_bump_info", return_value=l10n_bump_info)
    mocker.patch.object(l10n, "load_json_or_yaml", return_value=old_contents)
    mocker.patch.object(l10n, "get_latest_revision", new=noop_async)
    mocker.patch.object(l10n, "build_revision_dict", new=fake_build_revision_dict)
    mocker.patch.object(l10n, "vcs", new=AsyncMock())

    assert await l10n.l10n_bump({}, {}, tmpdir) == changes


@pytest.mark.asyncio
async def test_l10n_bump_closed_tree(mocker):
    """l10n_bump should exit if the tree is closed and ignore_closed_tree is
    False.

    """

    async def check_treestatus(*args):
        return False

    mocker.patch.object(l10n, "get_dontbuild", return_value=False)
    mocker.patch.object(l10n, "get_ignore_closed_tree", return_value=False)
    mocker.patch.object(l10n, "check_treestatus", new=check_treestatus)
    # this will [intentionally] break if we fail to exit l10n_bump where
    # we're supposed to
    mocker.patch.object(l10n, "get_l10n_bump_info", return_value=[{}])

    assert await l10n.l10n_bump({}, {}, "") == 0
