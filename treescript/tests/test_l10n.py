import os
import pytest

from scriptworker_client.utils import makedirs
import treescript.l10n as l10n


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
        "existing_different_rev": {
            "revision": "different_rev",
            "platforms": my_platforms,
        },
        "duplicate": my_dict,
        "existing_different_platforms": {
            "revision": my_rev,
            "platforms": ["different", "platforms"],
        },
        "existing_different_both": {
            "revision": "different_rev",
            "platforms": ["different", "platforms"],
        },
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
                    {
                        "platforms": ["android-api-16", "android"],
                        "path": "mobile/android/locales/all-locales",
                    },
                    {
                        "platforms": ["android-multilocale"],
                        "path": "mobile/android/locales/maemo-locales",
                    },
                ]
            },
            {
                "one": {
                    "platforms": ["android", "android-api-16", "android-multilocale"]
                },
                "two": {"platforms": ["android", "android-api-16"]},
                "three": {
                    "platforms": ["android", "android-api-16", "android-multilocale"]
                },
                "four": {"platforms": ["android", "android-api-16"]},
                "five": {
                    "platforms": ["android", "android-api-16", "android-multilocale"]
                },
                "six": {"platforms": ["android", "android-api-16"]},
            },
        ),
        (
            [
                """one x
two y
three z
ja a
ja-JP-mac b
"""
            ],
            {
                "ignore_config": {
                    "ja": ["macosx64", "macosx64-devedition"],
                    "ja-JP-mac": [
                        "linux",
                        "linux-devedition",
                        "linux64",
                        "linux64-devedition",
                    ],
                },
                "platform_configs": [
                    {
                        "platforms": [
                            "linux",
                            "linux-devedition",
                            "linux64",
                            "linux64-devedition",
                            "macosx64",
                            "macosx64-devedition",
                        ],
                        "path": "browser/locales/shipped-locales",
                        "format": "shipped-locales",
                    }
                ],
            },
            {
                "one": {
                    "platforms": [
                        "linux",
                        "linux-devedition",
                        "linux64",
                        "linux64-devedition",
                        "macosx64",
                        "macosx64-devedition",
                    ]
                },
                "two": {
                    "platforms": [
                        "linux",
                        "linux-devedition",
                        "linux64",
                        "linux64-devedition",
                        "macosx64",
                        "macosx64-devedition",
                    ]
                },
                "three": {
                    "platforms": [
                        "linux",
                        "linux-devedition",
                        "linux64",
                        "linux64-devedition",
                        "macosx64",
                        "macosx64-devedition",
                    ]
                },
                "ja": {
                    "platforms": [
                        "linux",
                        "linux-devedition",
                        "linux64",
                        "linux64-devedition",
                    ]
                },
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


# build_revision_dict {{{1
@pytest.mark.parametrize(
    "revision_info, expected",
    (
        (
            """one onerev
two tworev
three threerev
extra extrarev
""",
            {
                "one": {"revision": "onerev", "platforms": ["platform"]},
                "two": {"revision": "tworev", "platforms": ["platform"]},
                "three": {"revision": "threerev", "platforms": ["platform"]},
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
def test_build_revision_dict(mocker, revision_info, expected):
    """``build_revision_dict`` adds l10n dashboard revisions, if available,
    to the platform_dict; otherwise it adds a revision of "default" to
    every locale in the platform_dict.

    """
    platform_dict = {
        "one": {"platforms": ["platform"]},
        "two": {"platforms": ["platform"]},
        "three": {"platforms": ["platform"]},
    }

    def build_platform_dict(*args):
        return platform_dict

    mocker.patch.object(l10n, "build_platform_dict", new=build_platform_dict)
    assert l10n.build_revision_dict({}, revision_info, "") == expected


# build_commit_message {{{1
@pytest.mark.parametrize(
    "dontbuild, ignore_closed_tree", ((True, True), (False, False))
)
def test_build_commit_message(dontbuild, ignore_closed_tree):
    """build_commit_message adds the correct approval strings and a comment
    including the changes landed.
    """
    locale_map = {
        "a": "arev",
        "b": "brev",
        "c": "crev",
        "old": "removed",
        "p": ["platform"],
    }
    expected = [
        "no bug - Bumping foo r=release a=l10n-bump",
        "",
        "a -> arev",
        "b -> brev",
        "c -> crev",
        "old -> removed",
        "p -> ['platform']",
    ]
    if dontbuild:
        expected[0] += l10n.DONTBUILD_MSG
    if ignore_closed_tree:
        expected[0] += l10n.CLOSED_TREE_MSG
    assert (
        l10n.build_commit_message(
            "foo",
            locale_map,
            dontbuild=dontbuild,
            ignore_closed_tree=ignore_closed_tree,
        ).splitlines()
        == expected
    )


# check_treestatus {{{1
@pytest.mark.parametrize(
    "status, expected", (("open", True), ("closed", False), ("approval required", True))
)
@pytest.mark.asyncio
async def test_check_treestatus(status, mocker, expected):
    config = {"treestatus_base_url": "url", "work_dir": "foo"}
    treestatus = {
        "result": {
            "message_of_the_day": "",
            "reason": "",
            "status": status,
            "tree": "mozilla-central",
        }
    }
    mocker.patch.object(l10n, "download_file", new=noop_async)
    mocker.patch.object(l10n, "get_short_source_repo", return_value="tree")
    mocker.patch.object(l10n, "load_json_or_yaml", return_value=treestatus)
    assert await l10n.check_treestatus(config, {}) == expected
