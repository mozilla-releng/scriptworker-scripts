import json
import pytest
from scriptworker.client import TaskVerificationError
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT

from landoscript.script import async_main

from .conftest import assert_lando_submission_response, assert_status_response, setup_test, setup_fetch_files_response


def setup_treestatus_response(aioresponses, context, tree="repo_name", status="open", has_err=False):
    url = f'{context.config["treestatus_url"]}/trees/{tree}'
    if has_err:
        aioresponses.get(url, status=500)
    else:
        resp = {
            "result": {
                "category": "development",
                "log_id": 12345,
                "message_of_the_day": "",
                "reason": "",
                "status": status,
                "tags": [],
                "tree": tree,
            },
        }
        aioresponses.get(url, status=200, payload=resp)


def get_locale_block(locale, platforms, rev):
    # fmt: off
    locale_block = [
        f'    "{locale}": {{',
         '        "pin": false,',
         '        "platforms": ['
    ]
    platform_entries = []
    for platform in sorted(platforms):
        platform_entries.append(f'            "{platform}"')
    locale_block.extend(",\n".join(platform_entries).split("\n"))
    locale_block.extend([
         "        ],",
        f'        "revision": "{rev}"',
         # closing brace omitted because these blocks are used to generate
         # diffs, and in diffs, these end up using context from the subsequent
         # locale
         # "    }",
    ])
    # fmt: on

    return locale_block


def assert_l10n_bump_response(req, l10n_bump_info, expected_changes, initial_values, expected_values, dontbuild, ignore_closed_tree):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]
    assert len(create_commit_actions) == expected_changes

    for lbi in l10n_bump_info:
        name = lbi["name"]

        action = None
        for cca in create_commit_actions:
            if name in cca["commitmsg"]:
                action = cca

        if not action:
            assert False, f"couldn't find create-commit action for {name}!"

        if dontbuild:
            assert "DONTBUILD" in action["commitmsg"]

        if ignore_closed_tree:
            assert "CLOSED TREE" in action["commitmsg"]

        # ensure metadata is correct
        assert action["author"] == "Release Engineering Landoscript <release+landoscript@mozilla.com>"
        # we don't actually verify the value here; it's not worth the trouble of mocking
        assert "date" in action

        diffs = action["diff"].split("diff\n")
        assert len(diffs) == 1
        diff = diffs[0]

        initial_locales = set(initial_values[name]["locales"])
        expected_locales = set(expected_values[name]["locales"])
        initial_platforms = set(initial_values[name]["platforms"])
        expected_platforms = set(expected_values[name]["platforms"])
        added_locales = expected_locales - initial_locales
        removed_locales = initial_locales - expected_locales

        # ensure each expected locale has the new revision
        before_rev = initial_values[name]["revision"]
        after_rev = expected_values[name]["revision"]

        if before_rev != after_rev:
            revision_replacements = diff.count(f'-        "revision": "{before_rev}"\n+        "revision": "{after_rev}')
            # even if new locales are added, we only expect revision replacements
            # for initial ones that are not being removed. added locales are checked
            # further down.
            expected_revision_replacements = len(initial_locales - removed_locales)
            assert revision_replacements == expected_revision_replacements, "wrong number of revisions replaced!"

        # ensure any added locales are now present
        if added_locales:
            for locale in added_locales:
                expected = "+" + "\n+".join(get_locale_block(locale, expected_platforms, after_rev))
                assert expected in diff

        # ensure any removed locales are no longer present
        if removed_locales:
            for locale in removed_locales:
                expected = "-" + "\n-".join(get_locale_block(locale, expected_platforms, before_rev))
                assert expected in diff

        # ensure any added platforms are now present
        added_platforms = expected_platforms - initial_platforms
        for platform in added_platforms:
            expected_additions = len(expected_locales)
            for plats in lbi["ignore_config"].values():
                if platform in plats:
                    expected_additions -= 1
            expected = f'+            "{platform}"'
            assert diff.count(expected) == expected_additions

        # ensure any removed platforms are no longer present
        removed_platforms = initial_platforms - expected_platforms
        for platform in removed_platforms:
            expected_additions = len(expected_locales)
            for plats in lbi["ignore_config"].values():
                if platform in plats:
                    expected_additions -= 1
            expected = f'-            "{platform}"'
            assert diff.count(expected) == expected_additions


def setup_file_responses(aioresponses, l10n_bump_info, initial_values, expected_locales):
    file_responses = {}
    name = l10n_bump_info["name"]
    ignore_config = l10n_bump_info.get("ignore_config", {})
    revision = initial_values[name]["revision"]
    locales = initial_values[name]["locales"]
    platforms = initial_values[name]["platforms"]
    for pc in l10n_bump_info["platform_configs"]:
        file_responses[pc["path"]] = "\n".join(expected_locales)

    changesets_data = {}
    for locale in locales:
        locale_platforms = []
        for platform in platforms:
            if platform not in ignore_config.get(locale, []):
                locale_platforms.append(platform)

        changesets_data[locale] = {
            "pin": False,
            "platforms": [],
            "revision": revision,
            "platforms": sorted(locale_platforms),
        }

    file_responses[l10n_bump_info["path"]] = json.dumps(changesets_data)

    setup_fetch_files_response(aioresponses, 200, file_responses)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "l10n_bump_info,initial_values,expected_values,dry_run,dontbuild,ignore_closed_tree",
    (
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            True,
            False,
            False,
            id="dry_run",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            False,
            False,
            False,
            id="new_revision",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            False,
            True,
            False,
            id="dontbuild",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            False,
            False,
            True,
            id="ignore_closed_tree",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            False,
            True,
            True,
            id="dontbuild_ignore_closed_tree",
        ),
        pytest.param(
            [
                {
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Mobile l10n changesets",
                    "path": "mobile/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "mobile/android/locales/all-locales",
                            "platforms": ["android", "android-arm"],
                        }
                    ],
                }
            ],
            {
                "Mobile l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["de", "ja"],
                    "platforms": ["android", "android-arm"],
                },
            },
            {
                "Mobile l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["de", "ja"],
                    "platforms": ["android", "android-arm"],
                },
            },
            False,
            False,
            False,
            id="no_ignore_config",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                },
                {
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Mobile l10n changesets",
                    "path": "mobile/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "mobile/android/locales/all-locales",
                            "platforms": ["android", "android-arm"],
                        }
                    ],
                },
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
                "Mobile l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["de", "ja"],
                    "platforms": ["android", "android-arm"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
                "Mobile l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["de", "ja"],
                    "platforms": ["android", "android-arm"],
                },
            },
            False,
            False,
            False,
            id="multiple_bumps",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            False,
            False,
            False,
            id="no_new_revision",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "en-CA", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            False,
            False,
            False,
            id="new_locale",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            False,
            False,
            False,
            id="removed_locale",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "linux64-aarch64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "linux64-aarch64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "linux64-aarch64", "macosx64", "win64"],
                },
            },
            False,
            False,
            False,
            id="new_platform",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "linux64-aarch64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "linux64-aarch64", "macosx64", "win64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "linux64-aarch64", "macosx64", "win64"],
                },
            },
            False,
            False,
            False,
            id="new_platform_without_new_revision",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {
                        "ja": ["macosx64"],
                        "ja-JP-mac": ["linux64", "win64"],
                    },
                    "l10n_repo_target_branch": "main",
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64"],
                        }
                    ],
                }
            ],
            {
                "Firefox l10n changesets": {
                    "revision": "abcdef",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64", "win64"],
                },
            },
            {
                "Firefox l10n changesets": {
                    "revision": "ghijkl",
                    "locales": ["af", "ja", "ja-JP-mac", "zh-TW"],
                    "platforms": ["linux64", "macosx64"],
                },
            },
            False,
            False,
            False,
            id="removed_platform",
        ),
    ),
)
async def test_success(
    aioresponses, github_installation_responses, context, l10n_bump_info, initial_values, expected_values, dry_run, dontbuild, ignore_closed_tree
):

    payload = {
        "actions": ["l10n_bump"],
        "lando_repo": "repo_name",
        "l10n_bump_info": l10n_bump_info,
        "dry_run": dry_run,
        "dontbuild": dontbuild,
        "ignore_closed_tree": ignore_closed_tree,
    }
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["l10n_bump"])
    setup_treestatus_response(aioresponses, context)

    # because the github graphql endpoint is generic we need to make sure we create
    # these responses in the correct order...
    for lbi in l10n_bump_info:
        # this is called once for the repository we're bumping files in in
        # `setup_test`. we have to call it again for each bump info, because
        # the repository information exists in that part of the payload
        github_installation_responses("mozilla-l10n")
        setup_file_responses(aioresponses, lbi, initial_values, expected_values[lbi["name"]]["locales"])
        revision = expected_values[lbi["name"]]["revision"]
        aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"object": {"oid": revision}}}})

    if not dry_run:
        aioresponses.post(
            submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"}
        )

        aioresponses.get(
            status_uri,
            status=200,
            payload={
                "commits": ["abcdef123"],
                "push_id": job_id,
                "status": "completed",
            },
        )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    expected_changes = 0
    for initial_info, expected_info in zip(initial_values.values(), expected_values.values()):
        for k in initial_info.keys():
            if initial_info[k] != expected_info[k]:
                expected_changes += 1
                break

    for lbi in l10n_bump_info:
        name = lbi["name"]
        if initial_values[name] != expected_values[name]:
            assert (context.config["artifact_dir"] / f"public/build/l10n-bump-{name}.diff").exists()

    if not dry_run and expected_changes > 0:
        req = assert_lando_submission_response(aioresponses.requests, submit_uri)
        assert_l10n_bump_response(req, l10n_bump_info, expected_changes, initial_values, expected_values, dontbuild, ignore_closed_tree)
        assert_status_response(aioresponses.requests, status_uri)
    else:
        assert ("POST", submit_uri) not in aioresponses.requests
        assert ("GET", status_uri) not in aioresponses.requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "l10n_bump_info,errmsg",
    (
        pytest.param(
            [
                {
                    "ignore_config": {},
                    "l10n_repo_target_branch": "main",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                },
            ],
            "without an l10n_repo_url",
            id="no_l10n_repo_url",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {},
                    "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                },
            ],
            "l10n_repo_target_branch must be present",
            id="no_l10n_branch",
        ),
        pytest.param(
            [
                {
                    "ignore_config": {},
                    "name": "Firefox l10n changesets",
                    "path": "browser/locales/l10n-changesets.json",
                    "platform_configs": [
                        {
                            "path": "browser/locales/shipped-locales",
                            "platforms": ["linux64", "macosx64", "win64"],
                        }
                    ],
                },
            ],
            "without an l10n_repo_url",
            id="no_l10n_repo_url_or_branch",
        ),
    ),
)
async def test_l10n_repo_errors(aioresponses, github_installation_responses, context, l10n_bump_info, errmsg):

    payload = {
        "actions": ["l10n_bump"],
        "lando_repo": "repo_name",
        "l10n_bump_info": l10n_bump_info,
    }
    _, _, _, scopes = setup_test(github_installation_responses, context, payload, ["l10n_bump"])
    setup_treestatus_response(aioresponses, context)

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert errmsg in e.args[0]


@pytest.mark.asyncio
async def test_tree_is_closed_noop(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["l10n_bump"],
        "lando_repo": "repo_name",
        "l10n_bump_info": [
            {
                "ignore_config": {
                    "ja": ["macosx64"],
                    "ja-JP-mac": ["linux64", "win64"],
                },
                "l10n_repo_target_branch": "main",
                "l10n_repo_url": "https://github.com/mozilla-l10n/firefox-l10n",
                "name": "Firefox l10n changesets",
                "path": "browser/locales/l10n-changesets.json",
                "platform_configs": [
                    {
                        "path": "browser/locales/shipped-locales",
                        "platforms": ["linux64", "macosx64", "win64"],
                    }
                ],
            }
        ],
        "ignore_closed_tree": False,
    }
    submit_uri, status_uri, _, scopes = setup_test(github_installation_responses, context, payload, ["l10n_bump"])
    setup_treestatus_response(aioresponses, context, status="closed")

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert ("POST", submit_uri) not in aioresponses.requests
    assert ("GET", status_uri) not in aioresponses.requests
