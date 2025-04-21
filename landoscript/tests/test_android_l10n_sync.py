import pytest
from scriptworker_client.github_client import TransportQueryError
from pytest_scriptworker_client import get_files_payload

from landoscript.errors import LandoscriptError
from tests.conftest import (
    assert_add_commit_response,
    get_file_listing_payload,
    run_test,
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
    "android_l10n_sync_info,android_l10n_values,file_listing_files,initial_values,expected_values",
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
            [
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values/strings.xml",
            ],
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
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
            [
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values/strings.xml",
            ],
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": None,
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": None,
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": None,
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
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
            [
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values/strings.xml",
            ],
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": None,
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": None,
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": None,
            },
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
            [
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values/strings.xml",
            ],
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            id="no_changes",
        ),
    ),
)
async def test_success(
    aioresponses, github_installation_responses, context, android_l10n_sync_info, android_l10n_values, file_listing_files, initial_values, expected_values
):
    payload = {
        "actions": ["android_l10n_sync"],
        "lando_repo": "repo_name",
        "android_l10n_sync_info": android_l10n_sync_info,
    }

    setup_github_graphql_responses(
        aioresponses,
        # toml files needed before fetching anything else
        get_files_payload(
            {
                "mobile/android/fenix/l10n.toml": fenix_l10n_toml,
                "mobile/android/focus-android/l10n.toml": focus_l10n_toml,
                "mobile/android/android-components/l10n.toml": ac_l10n_toml,
            }
        ),
        # directory tree information needed to correctly interpret the
        # android-components l10n.toml
        get_file_listing_payload(file_listing_files),
        # string values in the android l10n repository
        get_files_payload(android_l10n_values),
        # current string values in the destination repository
        get_files_payload(initial_values),
    )

    def assert_func(req):
        assert_success(req, initial_values, expected_values)
        # check for diff on disk

    if initial_values == expected_values:
        should_submit = False
    else:
        should_submit = True

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
