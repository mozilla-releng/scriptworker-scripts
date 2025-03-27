import json
from os import major
import pytest
from scriptworker.client import TaskVerificationError
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT

from landoscript.script import async_main

from .conftest import assert_add_commit_response, assert_lando_submission_response, assert_status_response, setup_test, setup_fetch_files_response


def assert_merge_response(req, expected_actions, initial_values, expected_bumps, end_tag, base_tag={}, revision=""):
    actions = req.kwargs["json"]["actions"]
    action_names = [action["name"] for action in actions]
    assert action_names == expected_actions

    if base_tag:
        # base tag always happens first if we're expected it
        assert actions[0]["action"] == "tag"
        assert actions[0]["name"] == base_tag["name"]
        assert actions[0]["target"] == base_tag["target"]

    # `merge-onto` action w/ target revision, commit message, and `ours` strategy
    if revision:
        merge_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "merge-onto"]
        assert len(merge_actions) == 1
        action = merge_actions[0]
        assert action["target"] == revision
        assert action["strategy"] == "ours"
        assert action["message"] == "something"

    # `create-commit` action. check diff for:
    # - CLOBBER
    # - firefox version bumps
    # - `replacements` bumps
    # - `regex-replacements` bumps
    if expected_bumps:
        create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]
        assert len(create_commit_actions) == 1
        action = create_commit_actions[0]

        commit_msg_strings = ["something"]
        assert_add_commit_response(action, commit_msg_strings, initial_values, expected_bumps)

    if end_tag:
        tag_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "tag"]
        assert len(tag_actions) == 1
        action = tag_actions[0]
        assert action["name"] == end_tag
        # no target for end tags; they will tag the ref from the previous action


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "merge_info,dry_run,initial_values,expected_bumps,expected_actions,end_tag",
    (
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
                "to_repo": "https://hg.mozilla.org/mozilla-central",
                "to_branch": "central",
                "replacements": [
                    [
                        "services/sync/modules/constants.sys.mjs",
                        'WEAVE_VERSION = "1.{current_weave_version}.0"',
                        'WEAVE_VERSION = "1.{next_weave_version}.0"',
                    ]
                ],
                "version_files": [
                    {"filename": "config/milestone.txt", "new_suffix": "a1", "version_bump": "major"},
                    {"filename": "browser/config/version.txt", "new_suffix": "a1", "version_bump": "major"},
                    {"filename": "browser/config/version_display.txt", "new_suffix": "a1", "version_bump": "major"},
                    {"filename": "mobile/android/version.txt", "new_suffix": "a1", "version_bump": "major"},
                ],
                "merge_old_head": False,
                "fetch_version_from": "browser/config/version.txt",
            },
            False,
            {},
            {},
            ["create-commit", "tag"],
            "FIREFOX_NIGHTLY_140_END",
            id="bump_central",
        ),
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
                "to_repo": "https://hg.mozilla.org/mozilla-central",
                "to_branch": "central",
                "regex-replacements": [
                    [
                        "browser/extensions/webcompat/manifest.json",
                        '"version": "[0-9]+.[0-9]+.0"',
                        '"version": "{next_major_version}.0.0"',
                    ]
                ],
                "merge_old_head": False,
                "fetch_version_from": "browser/config/version.txt",
            },
            False,
            {},
            {},
            ["create-commit", "tag"],
            "FIREFOX_NIGHTLY_140_END",
            id="regex_replacements",
        ),
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
                "to_repo": "https://hg.mozilla.org/mozilla-central",
                "to_branch": "central",
                "replacements": [
                    [
                        "services/sync/modules/constants.sys.mjs",
                        'WEAVE_VERSION = "1.{current_weave_version}.0"',
                        'WEAVE_VERSION = "1.{next_weave_version}.0"',
                    ]
                ],
                "version_files": [
                    {"filename": "config/milestone.txt", "new_suffix": "a1", "version_bump": "major"},
                    {"filename": "browser/config/version.txt", "new_suffix": "a1", "version_bump": "major"},
                    {"filename": "browser/config/version_display.txt", "new_suffix": "a1", "version_bump": "major"},
                    {"filename": "mobile/android/version.txt", "new_suffix": "a1", "version_bump": "major"},
                ],
                "merge_old_head": False,
                "fetch_version_from": "browser/config/version.txt",
            },
            {},
            {},
            True,
            ["create-commit", "tag"],
            "FIREFOX_NIGHTLY_140_END",
            id="bump_central_dry_run",
        ),
    ),
)
async def test_success_bump_central(
    aioresponses, github_installation_responses, context, merge_info, dry_run, initial_values, expected_bumps, expected_actions, end_tag
):
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
        "dry_run": dry_run,
    }
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["l10n_bump"])

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

    assert (context.config["artifact_dir"] / f"public/build/central.diff").exists()

    if not dry_run:
        req = assert_lando_submission_response(aioresponses.requests, submit_uri)
        assert_merge_response(req, expected_actions, initial_values, expected_bumps, end_tag)
        assert_status_response(aioresponses.requests, status_uri)
    else:
        assert ("POST", submit_uri) not in aioresponses.requests
        assert ("GET", status_uri) not in aioresponses.requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "merge_info,initial_values,expected_bumps,expected_actions,end_tag,base_tag",
    (
        pytest.param(
            {
                "end_tag": "FIREFOX_BETA_{major_version}_END",
                "to_repo": "https://hg.mozilla.org/releases/mozilla-beta",
                "base_tag": "FIREFOX_BETA_{major_version}_BASE",
                "from_repo": "https://hg.mozilla.org/mozilla-central",
                "to_branch": "beta",
                "from_branch": "central",
                "replacements": [
                    [
                        "browser/config/mozconfigs/linux64/l10n-mozconfig",
                        "ac_add_options --with-branding=browser/branding/nightly",
                        "ac_add_options --enable-official-branding",
                    ],
                    [
                        "browser/config/mozconfigs/win32/l10n-mozconfig",
                        "ac_add_options --with-branding=browser/branding/nightly",
                        "ac_add_options --enable-official-branding",
                    ],
                    [
                        "browser/config/mozconfigs/win64/l10n-mozconfig",
                        "ac_add_options --with-branding=browser/branding/nightly",
                        "ac_add_options --enable-official-branding",
                    ],
                    [
                        "browser/config/mozconfigs/macosx64/l10n-mozconfig",
                        "ac_add_options --with-branding=browser/branding/nightly",
                        "ac_add_options --enable-official-branding",
                    ],
                    [".arcconfig", "MOZILLACENTRAL", "BETA"],
                ],
                "version_files": [
                    {"filename": "config/milestone.txt", "new_suffix": ""},
                    {"filename": "browser/config/version.txt", "new_suffix": ""},
                    {"filename": "browser/config/version_display.txt", "new_suffix": "b1"},
                    {"filename": "mobile/android/version.txt", "new_suffix": "b1"},
                ],
                "merge_old_head": True,
                "fetch_version_from": "browser/config/version.txt",
            },
            {},
            {},
            "FIREFOX_NIGHTLY_140_END",
            {
                "name": "FIREFOX_NIGHTLY_140_BASE",
                "ref": "ghijkl987654",
            },
            ["tag", "merge-onto", "create-commit", "tag"],
            id="central_to_beta",
        ),
        pytest.param(
            {
                "end_tag": "FIREFOX_RELEASE_{major_version}_END",
                "to_repo": "https://hg.mozilla.org/releases/mozilla-release",
                "base_tag": "FIREFOX_RELEASE_{major_version}_BASE",
                "from_repo": "https://hg.mozilla.org/releases/mozilla-beta",
                "to_branch": "release",
                "from_branch": "beta",
                "replacements": [[".arcconfig", "BETA", "RELEASE"]],
                "version_files": [
                    {"filename": "browser/config/version_display.txt", "new_suffix": ""},
                    {"filename": "mobile/android/version.txt", "new_suffix": ""},
                ],
                "merge_old_head": True,
                "fetch_version_from": "browser/config/version.txt",
            },
            {},
            {},
            "FIREFOX_NIGHTLY_140_END",
            {
                "name": "FIREFOX_NIGHTLY_140_BASE",
                "ref": "ghijkl987654",
            },
            ["tag", "merge-onto", "create-commit", "tag"],
            id="beta_to_release",
        ),
    ),
)
async def test_success_merge(
    aioresponses, github_installation_responses, context, merge_info, initial_values, expected_bumps, expected_actions, end_tag, base_tag
):
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["l10n_bump"])

    # set-up github response that returns tip commit of `from_branch`
    target_revision = "abcdef123456"

    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

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

    req = assert_lando_submission_response(aioresponses.requests, submit_uri)
    assert_merge_response(req, expected_actions, initial_values, expected_bumps, end_tag, base_tag, target_revision)
    assert_status_response(aioresponses.requests, status_uri)
