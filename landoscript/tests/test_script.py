from os import walk
from aiohttp import ClientResponseError
from collections import defaultdict
import pytest
from scriptworker.client import TaskVerificationError
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from pytest_scriptworker_client import get_files_payload

from landoscript.errors import LandoscriptError
from landoscript.script import async_main
from .conftest import (
    assert_l10n_bump_response,
    assert_lando_submission_response,
    assert_status_response,
    run_test,
    setup_github_graphql_responses,
    setup_test,
    assert_add_commit_response,
    setup_l10n_file_responses,
    assert_merge_response,
)
from .test_tag import assert_tag_response


def assert_success(artifact_dir, req, commit_msg_strings, initial_values, expected_bumps, has_actions=True):
    if has_actions:
        assert (artifact_dir / "public/build/lando-actions.json").exists()

    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]
    assert len(create_commit_actions) == 1
    action = create_commit_actions[0]

    assert_add_commit_response(action, commit_msg_strings, initial_values, expected_bumps)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings,dry_run",
    (
        pytest.param(
            {
                "actions": ["tag", "version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "tag_info": {
                    "revision": "abcdef123456",
                    "hg_repo_url": "https://hg.testing/repo",
                    "tags": ["RELEASE"],
                },
                "dry_run": True,
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            True,
            id="tag_and_bump",
        ),
        pytest.param(
            {
                "actions": ["tag", "version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "tag_info": {
                    "revision": "abcdef123456",
                    "hg_repo_url": "https://hg.testing/repo",
                    "tags": ["RELEASE"],
                },
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            False,
            id="tag_and_bump",
        ),
    ),
)
async def test_tag_and_bump(aioresponses, github_installation_responses, context, payload, dry_run, initial_values, expected_bumps, commit_msg_strings):
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    tag_info = payload["tag_info"]
    git_commit = "ghijkl654321"
    # TODO: update this URL when you figure out how to map land repos back to hg repos
    aioresponses.get(
        f"{tag_info['hg_repo_url']}/json-rev/{tag_info['revision']}",
        status=200,
        payload={
            # TODO: update this when you know what field this will be in
            "git_commit": git_commit
        },
    )

    def assert_func(req):
        assert_success(context.config["artifact_dir"], req, commit_msg_strings, initial_values, expected_bumps)
        assert_tag_response(req, tag_info, git_commit)
        assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()

    await run_test(aioresponses, github_installation_responses, context, payload, payload["actions"], not dry_run, assert_func)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings",
    (
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="one_file",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": [
                        "browser/config/version.txt",
                        "browser/config/version_display.txt",
                        "config/milestone.txt",
                        "mobile/android/version.txt",
                    ],
                    "next_version": "135.0",
                },
            },
            {
                "browser/config/version.txt": "134.0",
                "browser/config/version_display.txt": "134.0",
                "config/milestone.txt": "134.0",
                "mobile/android/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
                "browser/config/version_display.txt": "135.0",
                "config/milestone.txt": "135.0",
                "mobile/android/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="many_files",
        ),
    ),
)
async def test_success_with_retries(aioresponses, github_installation_responses, context, payload, initial_values, expected_bumps, commit_msg_strings):
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    aioresponses.post(submit_uri, status=500)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    aioresponses.get(status_uri, status=202, payload={"status": "pending", "job_id": job_id, "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
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
    await async_main(context)

    req = assert_lando_submission_response(aioresponses.requests, submit_uri, attempts=2)
    assert_success(context.config["artifact_dir"], req, commit_msg_strings, initial_values, expected_bumps)
    assert_status_response(aioresponses.requests, status_uri, attempts=2)
    assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()


@pytest.mark.asyncio
async def test_no_actions(aioresponses, github_installation_responses, context):
    payload = {
        "actions": [],
        "lando_repo": "repo_name",
    }
    await run_test(
        aioresponses, github_installation_responses, context, payload, ["tag"], err=TaskVerificationError, errmsg="must provide at least one action!"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scopes,missing",
    (
        pytest.param(
            [
                "project:releng:lando:action:tag",
                "project:releng:lando:action:version_bump",
            ],
            [
                "project:releng:lando:repo:repo_name",
            ],
            id="missing_repo_scope",
        ),
        pytest.param(
            [
                "project:releng:lando:repo:repo_name",
                "project:releng:lando:action:tag",
            ],
            [
                "project:releng:lando:action:version_bump",
            ],
            id="missing_one_action_scope",
        ),
        pytest.param(
            [
                "project:releng:lando:repo:repo_name",
            ],
            [
                "project:releng:lando:action:tag",
                "project:releng:lando:action:version_bump",
            ],
            id="missing_two_action_scopes",
        ),
        pytest.param(
            [],
            [
                "project:releng:lando:repo:repo_name",
                "project:releng:lando:action:tag",
                "project:releng:lando:action:version_bump",
            ],
            id="no_scopes",
        ),
    ),
)
async def test_missing_scopes(aioresponses, github_installation_responses, context, scopes, missing):
    payload = {
        "actions": ["tag", "version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }

    setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "required scope(s) not present" in e.args[0]
        for m in missing:
            assert m in e.args[0]


@pytest.mark.asyncio
async def test_dontbuild_properly_errors(aioresponses, github_installation_responses, context):
    payload = {"actions": ["tag"], "lando_repo": "repo_name", "tag_info": {"tags": ["FIREFOX_139_0_RELEASE"]}, "dontbuild": True}
    await run_test(
        aioresponses, github_installation_responses, context, payload, ["tag"], err=TaskVerificationError, errmsg="dontbuild is only respected in l10n_bump"
    )


@pytest.mark.asyncio
async def test_ignore_closed_tree_properly_errors(aioresponses, github_installation_responses, context):
    payload = {"actions": ["tag"], "lando_repo": "repo_name", "tag_info": {"tags": ["FIREFOX_139_0_RELEASE"]}, "ignore_closed_tree": True}
    await run_test(
        aioresponses,
        github_installation_responses,
        context,
        payload,
        ["tag"],
        err=TaskVerificationError,
        errmsg="ignore_closed_tree is only respected in l10n_bump and android_l10n_sync",
    )


@pytest.mark.asyncio
async def test_failure_to_submit_to_lando_500(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, _, _, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    for _ in range(10):
        aioresponses.post(submit_uri, status=500)

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised ClientResponseError"
    except ClientResponseError as e:
        assert e.status == 500


@pytest.mark.asyncio
async def test_to_submit_to_lando_no_status_url(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, _, _, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "couldn't find status url" in e.args[0]


@pytest.mark.asyncio
async def test_lando_polling_result_not_correct(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=200, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "status is not LANDED" in e.args[0]


@pytest.mark.parametrize("status", ["SUBMITTED", "IN_PROGRESS", "DEFERRED"])
@pytest.mark.asyncio
async def test_lando_200_status_retries(aioresponses, github_installation_responses, context, status):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": status,
        },
    )
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
    await async_main(context)

    assert_status_response(aioresponses.requests, status_uri, attempts=2)


@pytest.mark.asyncio
async def test_lando_polling_retry_on_failure(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=500, payload={})
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
    await async_main(context)

    assert_status_response(aioresponses.requests, status_uri, attempts=2)


@pytest.mark.asyncio
async def test_success_main_to_beta_merge_day(aioresponses, github_installation_responses, context):
    # despite it looking weird, these beta looking versions _are_ the correct
    # "before" versions after we've "merged" the main into beta
    initial_values = {
        "browser/config/version.txt": "139.0a1",
        "browser/config/version_display.txt": "139.0a1",
        "config/milestone.txt": "139.0a1",
        "mobile/android/version.txt": "139.0a1",
    }
    expected_bumps = {
        "browser/config/version.txt": "140.0",
        "browser/config/version_display.txt": "140.0b1",
        "config/milestone.txt": "140.0",
        "mobile/android/version.txt": "140.0b1",
    }
    initial_replacement_values = {
        ".arcconfig": '  "repository.callsign": "MOZILLACENTRAL",',
        "browser/config/mozconfigs/linux64/l10n-mozconfig": "ac_add_options --with-branding=browser/branding/nightly",
        "browser/config/mozconfigs/win32/l10n-mozconfig": "ac_add_options --with-branding=browser/branding/nightly",
        "browser/config/mozconfigs/win64/l10n-mozconfig": "ac_add_options --with-branding=browser/branding/nightly",
        "browser/config/mozconfigs/macosx64/l10n-mozconfig": "ac_add_options --with-branding=browser/branding/nightly",
    }
    expected_replacement_values = {
        ".arcconfig": '  "repository.callsign": "BETA",',
        "browser/config/mozconfigs/linux64/l10n-mozconfig": "ac_add_options --enable-official-branding",
        "browser/config/mozconfigs/win32/l10n-mozconfig": "ac_add_options --enable-official-branding",
        "browser/config/mozconfigs/win64/l10n-mozconfig": "ac_add_options --enable-official-branding",
        "browser/config/mozconfigs/macosx64/l10n-mozconfig": "ac_add_options --enable-official-branding",
    }
    # end tag, base tag, merge, version bump , replacements, mobile l10n bump, firefox l10n bump
    expected_actions = ["tag", "tag", "merge-onto", "create-commit", "create-commit", "create-commit", "create-commit"]
    base_tag = "FIREFOX_BETA_140_BASE"
    end_tag = "FIREFOX_BETA_139_END"
    initial_l10n_changesets = {
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
    }
    expected_l10n_changesets = {
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
    }
    l10n_bump_info = [
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
    ]
    merge_info = {
        "end_tag": "FIREFOX_BETA_{major_version}_END",
        "base_tag": "FIREFOX_BETA_{major_version}_BASE",
        "to_branch": "beta",
        "from_branch": "main",
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
    }
    payload = {
        "actions": ["merge_day", "l10n_bump"],
        "lando_repo": "repo_name",
        "l10n_bump_info": l10n_bump_info,
        "merge_info": merge_info,
        "ignore_closed_tree": True,
    }
    end_tag_target_ref = "ghijkl654321"
    base_tag_target_ref = "mnopqr987654"

    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["merge_day", "l10n_bump"])

    # version bump files are fetched in groups, by initial version
    initial_values_by_expected_version = defaultdict(dict)
    for file, version in expected_bumps.items():
        initial_values_by_expected_version[version][file] = initial_values[file]

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        get_files_payload({merge_info["fetch_version_from"]: "139.0b11"}),
        # branch ref for `end` tag
        {"data": {"repository": {"object": {"oid": end_tag_target_ref}}}},
        # existing version in `from_branch`
        get_files_payload({merge_info["fetch_version_from"]: "140.0a1"}),
        # branch ref for `base` tag
        {"data": {"repository": {"object": {"oid": base_tag_target_ref}}}},
        # fetch of original contents of files to bump
        *[get_files_payload(iv) for iv in initial_values_by_expected_version.values()],
        # fetch of original contents of `replacements` and `regex_replacements` files
        get_files_payload(initial_replacement_values),
        # clobber file
        get_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    # because the github graphql endpoint is generic we need to make sure we create
    # these responses in the correct order...
    for lbi in l10n_bump_info:
        # this is called once for the repository we're bumping files in in
        # `setup_test`. we have to call it again for each bump info, because
        # the repository information exists in that part of the payload
        github_installation_responses("mozilla-l10n")
        setup_l10n_file_responses(aioresponses, lbi, initial_l10n_changesets, expected_l10n_changesets[lbi["name"]]["locales"])
        revision = expected_l10n_changesets[lbi["name"]]["revision"]
        aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"object": {"oid": revision}}}})

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
    await async_main(context)

    req = assert_lando_submission_response(aioresponses.requests, submit_uri)
    assert_merge_response(
        context.config["artifact_dir"],
        req,
        expected_actions,
        initial_values,
        expected_bumps,
        initial_replacement_values,
        expected_replacement_values,
        end_tag,
        end_tag_target_ref,
        base_tag,
        base_tag_target_ref,
        base_tag_target_ref,
    )
    expected_changes = 0
    for initial_info, expected_info in zip(initial_l10n_changesets.values(), expected_l10n_changesets.values()):
        for k in initial_info.keys():
            if initial_info[k] != expected_info[k]:
                expected_changes += 1
                break

    assert_l10n_bump_response(req, l10n_bump_info, expected_changes, initial_l10n_changesets, expected_l10n_changesets)
    assert_status_response(aioresponses.requests, status_uri)
