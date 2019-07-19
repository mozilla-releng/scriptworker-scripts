import os
import pytest

from scriptworker_client.utils import makedirs
import treescript.l10n as l10n


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
