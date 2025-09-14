import pytest
from yarl import URL
from pytest_scriptworker_client import get_files_payload

from landoscript.errors import LandoscriptError
from landoscript.script import async_main
from tests.conftest import (
    assert_add_commit_response,
    assert_lando_submission_response,
    assert_status_response,
    setup_github_graphql_responses,
)

ac_l10n_toml = """
basepath = "."

locales = [
    "ab",
]

[env]

[[paths]]
  reference = "components/**/src/main/res/values/strings.xml"
  l10n = "components/**/src/main/res/values-{android_locale}/strings.xml"
"""

ac_l10n_toml_new_locale = """
basepath = "."

locales = [
    "ab",
    "de",
]

[env]

[[paths]]
  reference = "components/**/src/main/res/values/strings.xml"
  l10n = "components/**/src/main/res/values-{android_locale}/strings.xml"
"""

fenix_l10n_toml = """
basepath = "."

locales = [
    "my",
]

[env]

[[paths]]
  reference = "app/src/main/res/values/strings.xml"
  l10n = "app/src/main/res/values-{android_locale}/strings.xml"
"""

fenix_l10n_toml_removed_locale = """
basepath = "."

locales = [
    "zh",
]

[env]

[[paths]]
  reference = "app/src/main/res/values/strings.xml"
  l10n = "app/src/main/res/values-{android_locale}/strings.xml"
"""

focus_l10n_toml = """
basepath = "."

locales = [
    "zam",
]

[env]

[[paths]]
  reference = "app/src/main/res/values/strings.xml"
  l10n = "app/src/main/res/values-{android_locale}/strings.xml"
"""


def assert_success(req, initial_values, expected_bumps):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]
    assert len(create_commit_actions) == 1
    action = create_commit_actions[0]

    assert_add_commit_response(action, ["Import translations from", "CLOSED TREE"], initial_values, expected_bumps)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "android_l10n_import_info,android_l10n_values,initial_values,expected_values,ac_toml,fenix_toml,focus_toml",
    (
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            ac_l10n_toml,
            fenix_l10n_toml,
            focus_l10n_toml,
            id="import",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": None,
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": None,
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": None,
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            ac_l10n_toml,
            fenix_l10n_toml,
            focus_l10n_toml,
            id="new files",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml": None,
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": None,
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": None,
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": None,
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": None,
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": None,
            },
            ac_l10n_toml,
            fenix_l10n_toml,
            focus_l10n_toml,
            id="removed file",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            ac_l10n_toml,
            fenix_l10n_toml,
            focus_l10n_toml,
            id="no_changes",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-de/strings.xml": "de initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-de/strings.xml": None,
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml_new_locale,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-de/strings.xml": "de initial contents",
            },
            ac_l10n_toml_new_locale,
            fenix_l10n_toml,
            focus_l10n_toml,
            id="toml_file_added_locale",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-zh/strings.xml": "zh initial contents",
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-zh/strings.xml": None,
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml_removed_locale,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": None,
                "mobile/android/fenix/app/src/main/res/values-zh/strings.xml": "zh initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            ac_l10n_toml,
            fenix_l10n_toml_removed_locale,
            focus_l10n_toml,
            id="toml_file_removed_locale",
        ),
    ),
)
async def test_success(
    aioresponses,
    github_installation_responses,
    context,
    android_l10n_import_info,
    android_l10n_values,
    initial_values,
    expected_values,
    ac_toml,
    fenix_toml,
    focus_toml,
):
    payload = {
        "actions": ["android_l10n_import"],
        "lando_repo": "repo_name",
        "android_l10n_import_info": android_l10n_import_info,
    }
    # this is the same setup that's done in `setup_test`, but in a slightly different
    # order to accommodate the fact that we query the `mozilla-l10n` repository before
    # the `lando_repo` repository.
    from yarl import URL

    lando_repo = payload["lando_repo"]
    lando_api = context.config["lando_api"]
    owner = "faker"
    repo_info_uri = URL(f"{lando_api}/repoinfo/repo_name")
    submit_uri = URL(f"{lando_api}/repo/{lando_repo}")
    job_id = 12345
    status_uri = URL(f"{lando_api}/job/{job_id}")

    scopes = [f"project:releng:lando:repo:repo_name"]
    scopes.append(f"project:releng:lando:action:android_l10n_import")

    file_listing_payloads = [
        {
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {
                                "name": "components",
                                "type": "tree",
                                "object": {
                                    "entries": [
                                        {
                                            "name": "browser",
                                            "type": "tree",
                                            "object": {
                                                "entries": [
                                                    {
                                                        "name": "toolbar",
                                                        "type": "tree",
                                                        "object": {
                                                            "entries": [
                                                                {
                                                                    "name": "src",
                                                                    "type": "tree",
                                                                }
                                                            ],
                                                        },
                                                    }
                                                ],
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                },
            },
        },
        {
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {
                                "name": "main",
                                "type": "tree",
                                "object": {
                                    "entries": [
                                        {
                                            "name": "res",
                                            "type": "tree",
                                            "object": {
                                                "entries": [
                                                    {
                                                        "name": "values",
                                                        "type": "tree",
                                                        "object": {
                                                            "entries": [
                                                                {
                                                                    "name": "strings.xml",
                                                                    "type": "blob",
                                                                    "object": {},
                                                                }
                                                            ]
                                                        },
                                                    }
                                                ],
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                },
            },
        },
    ]
    github_installation_responses("mozilla-l10n")
    setup_github_graphql_responses(
        aioresponses,
        # toml files needed before fetching anything else
        get_files_payload(
            {
                "mozilla-mobile/fenix/l10n.toml": fenix_toml,
                "mozilla-mobile/focus-android/l10n.toml": focus_toml,
                "mozilla-mobile/android-components/l10n.toml": ac_toml,
            }
        ),
        # directory tree information needed to correctly interpret the
        # android-components l10n.toml
        *file_listing_payloads,
        # string values in the android l10n repository
        get_files_payload(android_l10n_values),
    )

    aioresponses.get(
        repo_info_uri,
        status=200,
        payload={
            "repo_url": f"https://github.com/{owner}/repo_name",
            "branch_name": "fake_branch",
            "scm_level": "whatever",
        },
    )

    github_installation_responses(owner)
    # current string values in the destination repository
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "LANDED",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}
    print('contextt', context)
    await async_main(context)

    expected_bumps = {k: v for k, v in expected_values.items() if initial_values.get(k) != v}
    if expected_bumps:
        req = assert_lando_submission_response(aioresponses.requests, submit_uri)
        assert_success(req, initial_values, expected_bumps)
        assert_status_response(aioresponses.requests, status_uri)
    else:
        assert ("POST", submit_uri) not in aioresponses.requests
        assert ("GET", status_uri) not in aioresponses.requests


@pytest.mark.asyncio
async def test_missing_toml_file(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["android_l10n_import"],
        "lando_repo": "repo_name",
        "android_l10n_import_info": {
            "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
            "toml_info": [
                {
                    "dest_path": "mobile/android/fenix",
                    "toml_path": "mozilla-mobile/fenix/l10n.toml",
                },
                {
                    "dest_path": "mobile/android/focus-android",
                    "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                },
                {
                    "dest_path": "mobile/android/android-components",
                    "toml_path": "mozilla-mobile/android-components/l10n.toml",
                },
            ],
        },
    }

    scopes = [f"project:releng:lando:repo:repo_name"]
    scopes.append(f"project:releng:lando:action:android_l10n_import")

    lando_api = context.config["lando_api"]
    repo_info_uri = URL(f"{lando_api}/repoinfo/repo_name")
    aioresponses.get(
        repo_info_uri,
        status=200,
        payload={
            "repo_url": f"https://github.com/faker/repo_name",
            "branch_name": "fake_branch",
            "scm_level": "whatever",
        },
    )

    github_installation_responses("mozilla-l10n")
    setup_github_graphql_responses(
        aioresponses,
        # toml files needed before fetching anything else
        get_files_payload(
            {
                "mozilla-mobile/fenix/l10n.toml": None,
                "mozilla-mobile/focus-android/l10n.toml": focus_l10n_toml,
                "mozilla-mobile/android-components/l10n.toml": ac_l10n_toml,
            }
        ),
    )

    context.task = {"payload": payload, "scopes": scopes}
    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "toml_file(s) mozilla-mobile/fenix/l10n.toml are not present" in e.args[0]
