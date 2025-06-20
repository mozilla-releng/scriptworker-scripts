from collections import defaultdict
import pytest
from pytest_scriptworker_client import get_files_payload
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT

from landoscript.actions import merge_day
from landoscript.script import async_main

from .conftest import (
    assert_l10n_bump_response,
    assert_lando_submission_response,
    assert_status_response,
    run_test,
    assert_merge_response,
    setup_github_graphql_responses,
    setup_l10n_file_responses,
    setup_test,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "merge_info,dry_run,initial_values,expected_bumps,initial_replacement_values,expected_replacement_bumps,expected_actions,end_tag",
    (
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
                "to_branch": "main",
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
            {
                "browser/config/version.txt": "137.0a1",
                "browser/config/version_display.txt": "137.0a1",
                "config/milestone.txt": "137.0a1",
                "mobile/android/version.txt": "137.0a1",
            },
            {
                "browser/config/version.txt": "138.0a1",
                "browser/config/version_display.txt": "138.0a1",
                "config/milestone.txt": "138.0a1",
                "mobile/android/version.txt": "138.0a1",
            },
            {
                "services/sync/modules/constants.sys.mjs": 'export const WEAVE_VERSION = "1.139.0";',
            },
            {
                "services/sync/modules/constants.sys.mjs": 'export const WEAVE_VERSION = "1.140.0";',
            },
            # end tag, bump configs, bump replacements
            ["tag", "create-commit", "create-commit"],
            "FIREFOX_NIGHTLY_137_END",
            id="bump_main",
        ),
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
                "to_branch": "main",
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
            True,
            {
                "browser/config/version.txt": "137.0a1",
                "browser/config/version_display.txt": "137.0a1",
                "config/milestone.txt": "137.0a1",
                "mobile/android/version.txt": "137.0a1",
            },
            {
                "browser/config/version.txt": "138.0a1",
                "browser/config/version_display.txt": "138.0a1",
                "config/milestone.txt": "138.0a1",
                "mobile/android/version.txt": "138.0a1",
            },
            {
                "services/sync/modules/constants.sys.mjs": 'export const WEAVE_VERSION = "1.139.0";',
            },
            {
                "services/sync/modules/constants.sys.mjs": 'export const WEAVE_VERSION = "1.140.0";',
            },
            # end tag, bump configs, bump replacements
            ["tag", "create-commit", "create-commit"],
            "FIREFOX_NIGHTLY_137_END",
            id="bump_main_dry_run",
        ),
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
                "to_branch": "main",
                "regex_replacements": [
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
            {
                "browser/config/version.txt": "137.0a1",
            },
            {},
            {
                "browser/extensions/webcompat/manifest.json": '{"version": "137.5.0"}\n',
            },
            {
                "browser/extensions/webcompat/manifest.json": '{"version": "138.0.0"}\n',
            },
            # end tag, bump replacements
            ["tag", "create-commit"],
            "FIREFOX_NIGHTLY_137_END",
            id="regex_replacements",
        ),
    ),
)
async def test_success_bump_main(
    patch_date,
    aioresponses,
    github_installation_responses,
    context,
    merge_info,
    dry_run,
    initial_values,
    expected_bumps,
    initial_replacement_values,
    expected_replacement_bumps,
    expected_actions,
    end_tag,
):
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
        "dry_run": dry_run,
    }

    end_tag_target_ref = "ghijkl654321"

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        get_files_payload({merge_info["fetch_version_from"]: "137.0a1"}),
        # branch ref for `end` tag
        {"data": {"repository": {"object": {"oid": end_tag_target_ref}}}},
        # fetch of original contents of files to bump, if we expect any replacements
        get_files_payload(initial_values if expected_bumps else {}),
        # fetch of original contents of `replacements` and `regex_replacements` files
        get_files_payload(initial_replacement_values if expected_replacement_bumps else {}),
        # clobber file
        get_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    patch_date(merge_day, 2025, 6, 10)

    def assert_func(req):
        initial_replacement_values["CLOBBER"] = "Merge day clobber 2025-03-03\n\\No newline at end of file"
        expected_replacement_bumps["CLOBBER"] = "Merge day clobber 2025-06-10\n\\No newline at end of file"
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
            initial_replacement_values,
            expected_replacement_bumps,
            end_tag,
            end_tag_target_ref,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], not dry_run, assert_func)


@pytest.mark.asyncio
async def test_success_bump_esr(patch_date, aioresponses, github_installation_responses, context):
    merge_info = {
        "to_branch": "esr128",
        "version_files": [
            {"filename": "config/milestone.txt", "version_bump": "minor"},
            {"filename": "browser/config/version.txt", "version_bump": "minor"},
            {"filename": "browser/config/version_display.txt", "new_suffix": "esr", "version_bump": "minor"},
        ],
        "merge_old_head": False,
        "fetch_version_from": "browser/config/version.txt",
    }
    initial_values = {
        "browser/config/version.txt": "128.9.0",
        "browser/config/version_display.txt": "128.9.0esr",
        "config/milestone.txt": "128.9.0",
    }
    expected_bumps = {
        "browser/config/version.txt": "128.10.0",
        "browser/config/version_display.txt": "128.10.0esr",
        "config/milestone.txt": "128.10.0",
    }
    # end tag, bump configs, bump replacements
    expected_actions = ["create-commit", "create-commit"]
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }

    # version bump files are fetched in groups, by initial version
    initial_values_by_expected_version = defaultdict(dict)
    for file, version in expected_bumps.items():
        initial_values_by_expected_version[version][file] = initial_values[file]

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        get_files_payload({merge_info["fetch_version_from"]: "128.9.0"}),
        # fetch of original contents of files to bump
        *[get_files_payload(iv) for iv in initial_values_by_expected_version.values()],
        # clobber file
        get_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    patch_date(merge_day, 2025, 6, 10)

    def assert_func(req):
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
            {"CLOBBER": "Merge day clobber 2025-03-03\n\\No newline at end of file"},
            {"CLOBBER": "Merge day clobber 2025-06-10\n\\No newline at end of file"},
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], True, assert_func=assert_func)


@pytest.mark.asyncio
async def test_success_early_to_late_beta(patch_date, aioresponses, github_installation_responses, context):
    merge_info = {
        "to_branch": "beta",
        "replacements": [
            [
                "build/defines.sh",
                "EARLY_BETA_OR_EARLIER=1",
                "EARLY_BETA_OR_EARLIER=",
            ],
        ],
        "merge_old_head": False,
        "fetch_version_from": "browser/config/version.txt",
    }
    initial_replacement_values = {"build/defines.sh": "EARLY_BETA_OR_EARLIER=1\n"}
    expected_replacement_bumps = {"build/defines.sh": "EARLY_BETA_OR_EARLIER=\n"}
    # bump configs
    expected_actions = ["create-commit"]
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }

    setup_github_graphql_responses(
        aioresponses,
        # initial version fetch; technically not needed for this use case
        # but it keeps the merge day code cleaner to keep it
        get_files_payload({merge_info["fetch_version_from"]: "139.0"}),
        # fetch of original contents of `replacements` file
        get_files_payload(initial_replacement_values),
        # clobber file
        get_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    patch_date(merge_day, 2025, 6, 10)

    def assert_func(req):
        initial_replacement_values["CLOBBER"] = "Merge day clobber 2025-03-03\n\\No newline at end of file"
        expected_replacement_bumps["CLOBBER"] = "Merge day clobber 2025-06-10\n\\No newline at end of file"
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            {},
            {},
            initial_replacement_values,
            expected_replacement_bumps,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], assert_func=assert_func)


@pytest.mark.asyncio
async def test_success_main_to_beta_merge_day(patch_date, aioresponses, github_installation_responses, context):
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
    }
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }
    end_tag_target_ref = "ghijkl654321"
    base_tag_target_ref = "mnopqr987654"

    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["merge_day"])

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
    )

    # because the github graphql endpoint is generic we need to make sure we create
    # these responses in the correct order...
    for lbi in payload["merge_info"]["l10n_bump_info"]:
        # this is called once for the repository we're bumping files in in
        # `setup_test`. we have to call it again for each bump info, because
        # the repository information exists in that part of the payload
        github_installation_responses("mozilla-l10n")
        setup_l10n_file_responses(aioresponses, lbi, initial_l10n_changesets, expected_l10n_changesets[lbi["name"]]["locales"])
        revision = expected_l10n_changesets[lbi["name"]]["revision"]
        aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"object": {"oid": revision}}}})

    setup_github_graphql_responses(
        aioresponses,
        # fetch of original contents of files to bump
        *[get_files_payload(iv) for iv in initial_values_by_expected_version.values()],
        # fetch of original contents of `replacements` and `regex_replacements` files
        get_files_payload(initial_replacement_values),
        # clobber file
        get_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    patch_date(merge_day, 2025, 6, 10)

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

    initial_replacement_values["CLOBBER"] = "Merge day clobber 2025-03-03\n\\No newline at end of file"
    expected_replacement_values["CLOBBER"] = "Merge day clobber 2025-06-10\n\\No newline at end of file"
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

    assert_l10n_bump_response(req, payload["merge_info"]["l10n_bump_info"], expected_changes, initial_l10n_changesets, expected_l10n_changesets)
    assert_status_response(aioresponses.requests, status_uri)


@pytest.mark.asyncio
async def test_success_beta_to_release(patch_date, aioresponses, github_installation_responses, context):
    merge_info = {
        "end_tag": "FIREFOX_RELEASE_{major_version}_END",
        "base_tag": "FIREFOX_RELEASE_{major_version}_BASE",
        "to_branch": "release",
        "from_branch": "beta",
        "replacements": [[".arcconfig", "BETA", "RELEASE"]],
        "version_files": [
            {"filename": "browser/config/version_display.txt", "new_suffix": ""},
            {"filename": "mobile/android/version.txt", "new_suffix": ""},
        ],
        "merge_old_head": True,
        "fetch_version_from": "browser/config/version.txt",
    }
    # despite it looking weird, these beta looking versions _are_ the correct
    # "before" versions after we've "merged" the beta branch into release
    initial_values = {
        "browser/config/version_display.txt": "136.0b11",
        "mobile/android/version.txt": "136.0b11",
    }
    expected_bumps = {
        "browser/config/version_display.txt": "136.0",
        "mobile/android/version.txt": "136.0",
    }
    initial_replacement_values = {
        ".arcconfig": '  "repository.callsign": "BETA",',
    }
    expected_replacement_values = {
        ".arcconfig": '  "repository.callsign": "RELEASE",',
    }
    # end tag, base tag, merge, version bump, replacements
    expected_actions = ["tag", "tag", "merge-onto", "create-commit", "create-commit"]
    base_tag = "FIREFOX_RELEASE_136_BASE"
    end_tag = "FIREFOX_RELEASE_135_END"
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }
    end_tag_target_ref = "ghijkl654321"
    base_tag_target_ref = "mnopqr987654"

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        get_files_payload({merge_info["fetch_version_from"]: "135.0"}),
        # branch ref for `end` tag
        {"data": {"repository": {"object": {"oid": end_tag_target_ref}}}},
        # existing version in `from_branch`
        get_files_payload({merge_info["fetch_version_from"]: "136.0"}),
        # branch ref for `base` tag
        {"data": {"repository": {"object": {"oid": base_tag_target_ref}}}},
        # fetch of original contents of files to bump, if we expect any replacements
        get_files_payload(initial_values),
        # fetch of original contents of `replacements` and `regex_replacements` files
        get_files_payload(initial_replacement_values),
        # clobber file
        get_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    patch_date(merge_day, 2025, 6, 10)

    def assert_func(req):
        initial_replacement_values["CLOBBER"] = "Merge day clobber 2025-03-03\n\\No newline at end of file"
        expected_replacement_values["CLOBBER"] = "Merge day clobber 2025-06-10\n\\No newline at end of file"
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

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], assert_func=assert_func)


@pytest.mark.asyncio
async def test_success_release_to_esr(patch_date, aioresponses, github_installation_responses, context):
    merge_info = {
        # yep...we use `BASE` on the `end_tag` for release-to-esr merges
        "end_tag": "FIREFOX_ESR_{major_version}_BASE",
        "to_branch": "esr128",
        "replacements": [[".arcconfig", "RELEASE", "ESRONETWOEIGHT"]],
        "version_files": [
            {"filename": "browser/config/version_display.txt", "new_suffix": "esr"},
        ],
        "merge_old_head": False,
        "fetch_version_from": "browser/config/version.txt",
    }
    initial_values = {
        "browser/config/version_display.txt": "128.0",
    }
    expected_bumps = {
        "browser/config/version_display.txt": "128.0esr",
    }
    initial_replacement_values = {
        ".arcconfig": '  "repository.callsign": "RELEASE",',
    }
    expected_replacement_bumps = {
        ".arcconfig": '  "repository.callsign": "ESRONETWOEIGHT",',
    }
    # end tag, version bump, replacements
    expected_actions = ["tag", "create-commit", "create-commit"]
    end_tag = "FIREFOX_ESR_128_BASE"
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }
    end_tag_target_ref = "ghijkl654321"

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        get_files_payload({merge_info["fetch_version_from"]: "128.0"}),
        # branch ref for `end` tag
        {"data": {"repository": {"object": {"oid": end_tag_target_ref}}}},
        # fetch of original contents of files to bump, if we expect any replacements
        get_files_payload(initial_values if expected_bumps else {}),
        # fetch of original contents of `replacements` and `regex_replacements` files
        get_files_payload(initial_replacement_values),
        # clobber file
        get_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    patch_date(merge_day, 2025, 6, 10)

    def assert_func(req):
        initial_replacement_values["CLOBBER"] = "Merge day clobber 2025-03-03\n\\No newline at end of file"
        expected_replacement_bumps["CLOBBER"] = "Merge day clobber 2025-06-10\n\\No newline at end of file"
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
            initial_replacement_values,
            expected_replacement_bumps,
            end_tag,
            end_tag_target_ref,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], assert_func=assert_func)
