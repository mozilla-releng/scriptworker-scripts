import pytest
from scriptworker_client.github_client import TransportQueryError
from pytest_scriptworker_client import get_files_payload

from landoscript.errors import LandoscriptError
from landoscript.script import async_main
from tests.conftest import (
    assert_add_commit_response,
    run_test,
    setup_github_graphql_responses,
    setup_test,
    setup_treestatus_response,
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

    assert_add_commit_response(action, ["Import translations from"], initial_values, expected_bumps)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "android_l10n_sync_info,android_l10n_values,initial_values,expected_values,ac_toml,fenix_toml,focus_toml",
    (
        pytest.param(
            {
                "from_branch": "main",
                "toml_info": [
                    {
                        "toml_path": "mobile/android/fenix/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/focus-android/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/android-components/l10n.toml",
                    },
                ],
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            {
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
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
            id="only_changes",
        ),
        pytest.param(
            {
                "from_branch": "main",
                "toml_info": [
                    {
                        "toml_path": "mobile/android/fenix/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/focus-android/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/android-components/l10n.toml",
                    },
                ],
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            {
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": None,
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": None,
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": None,
            },
            {
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
                "from_branch": "main",
                "toml_info": [
                    {
                        "toml_path": "mobile/android/fenix/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/focus-android/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/android-components/l10n.toml",
                    },
                ],
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": None,
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": None,
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": None,
            },
            {
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
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
                "from_branch": "main",
                "toml_info": [
                    {
                        "toml_path": "mobile/android/fenix/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/focus-android/l10n.toml",
                    },
                    {
                        "toml_path": "mobile/android/android-components/l10n.toml",
                    },
                ],
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
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
    ),
)
async def test_success(
    aioresponses,
    github_installation_responses,
    context,
    android_l10n_sync_info,
    android_l10n_values,
    initial_values,
    expected_values,
    ac_toml,
    fenix_toml,
    focus_toml,
):
    payload = {
        "actions": ["android_l10n_sync"],
        "lando_repo": "repo_name",
        "android_l10n_sync_info": android_l10n_sync_info,
        "ignore_closed_tree": False,
    }

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

    setup_treestatus_response(aioresponses, context, status="open")
    setup_github_graphql_responses(
        aioresponses,
        # toml files needed before fetching anything else
        get_files_payload(
            {
                "mobile/android/fenix/l10n.toml": fenix_toml,
                "mobile/android/focus-android/l10n.toml": focus_toml,
                "mobile/android/android-components/l10n.toml": ac_toml,
            }
        ),
        # directory tree information needed to correctly interpret the
        # android-components l10n.toml
        *file_listing_payloads,
        # string values in the android l10n repository
        get_files_payload(android_l10n_values),
        # current string values in the destination repository
        get_files_payload(initial_values),
    )

    expected_bumps = {k: v for k, v in expected_values.items() if initial_values.get(k) != v}

    def assert_func(req):
        if expected_bumps:
            assert_success(req, initial_values, expected_bumps)

    if expected_bumps:
        should_submit = True
    else:
        should_submit = False

    await run_test(aioresponses, github_installation_responses, context, payload, ["android_l10n_sync"], should_submit, assert_func)


@pytest.mark.asyncio
async def test_missing_toml_file(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["android_l10n_sync"],
        "lando_repo": "repo_name",
        "android_l10n_sync_info": {
            "from_branch": "main",
            "toml_info": [
                {
                    "toml_path": "mobile/android/fenix/l10n.toml",
                },
                {
                    "toml_path": "mobile/android/focus-android/l10n.toml",
                },
                {
                    "toml_path": "mobile/android/android-components/l10n.toml",
                },
            ],
        },
    }

    setup_github_graphql_responses(
        aioresponses,
        # toml files needed before fetching anything else
        get_files_payload(
            {
                "mobile/android/fenix/l10n.toml": None,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
            }
        ),
    )

    await run_test(
        aioresponses,
        github_installation_responses,
        context,
        payload,
        ["android_l10n_sync"],
        err=LandoscriptError,
        errmsg="toml_file(s) mobile/android/fenix/l10n.toml are not present",
    )


@pytest.mark.asyncio
async def test_tree_is_closed_noop(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["android_l10n_sync"],
        "lando_repo": "repo_name",
        "android_l10n_sync_info": {
            "from_branch": "main",
            "toml_info": [
                {
                    "toml_path": "mobile/android/fenix/l10n.toml",
                },
                {
                    "toml_path": "mobile/android/focus-android/l10n.toml",
                },
                {
                    "toml_path": "mobile/android/android-components/l10n.toml",
                },
            ],
        },
        "ignore_closed_tree": False,
    }
    submit_uri, status_uri, _, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["android_l10n_sync"])
    setup_treestatus_response(aioresponses, context, status="closed")

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert ("POST", submit_uri) not in aioresponses.requests
    assert ("GET", status_uri) not in aioresponses.requests
