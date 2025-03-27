import pytest
from scriptworker.client import TaskVerificationError
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT

from landoscript.script import async_main

from .conftest import assert_lando_submission_response, assert_status_response, setup_test, setup_l10n_file_responses, assert_l10n_bump_response


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
        setup_l10n_file_responses(aioresponses, lbi, initial_values, expected_values[lbi["name"]]["locales"])
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
