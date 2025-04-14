from collections import defaultdict
import pytest

from landoscript.script import async_main

from .conftest import fetch_files_payload, run_test, assert_merge_response, setup_github_graphql_responses


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "merge_info,dry_run,initial_values,expected_bumps,initial_replacement_values,expected_replacement_bumps,expected_actions,end_tag",
    (
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
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
            id="bump_central",
        ),
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
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
            id="bump_central_dry_run",
        ),
        pytest.param(
            {
                "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
                "to_branch": "central",
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
async def test_success_bump_central(
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

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        fetch_files_payload({merge_info["fetch_version_from"]: "137.0a1"}),
        # fetch of original contents of files to bump, if we expect any replacements
        fetch_files_payload(initial_values if expected_bumps else {}),
        # fetch of original contents of `replacements` and `regex_replacements` files
        fetch_files_payload(initial_replacement_values if expected_replacement_bumps else {}),
        # clobber file
        fetch_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    def assert_func(req):
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
            initial_replacement_values,
            expected_replacement_bumps,
            end_tag,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], not dry_run, assert_func)


@pytest.mark.asyncio
async def test_success_bump_esr(aioresponses, github_installation_responses, context):
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
        fetch_files_payload({merge_info["fetch_version_from"]: "128.9.0"}),
        # fetch of original contents of files to bump
        *[fetch_files_payload(iv) for iv in initial_values_by_expected_version.values()],
        # clobber file
        fetch_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    def assert_func(req):
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], True, assert_func=assert_func)


@pytest.mark.asyncio
async def test_success_early_to_late_beta(aioresponses, github_installation_responses, context):
    merge_info = {
        "to_branch": "beta",
        "version_files": [],
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
        fetch_files_payload({merge_info["fetch_version_from"]: "139.0"}),
        # fetch of original contents of `replacements` file
        fetch_files_payload(initial_replacement_values),
        # clobber file
        fetch_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    def assert_func(req):
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
async def test_success_central_to_beta(aioresponses, github_installation_responses, context):
    merge_info = {
        "end_tag": "FIREFOX_BETA_{major_version}_END",
        "base_tag": "FIREFOX_BETA_{major_version}_BASE",
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
    }
    # despite it looking weird, these beta looking versions _are_ the correct
    # "before" versions after we've "merged" central into beta
    initial_values = {
        "browser/config/version.txt": "140.0a1",
        "browser/config/version_display.txt": "140.0a1",
        "config/milestone.txt": "140.0a1",
        "mobile/android/version.txt": "140.0a1",
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
    # end tag, base tag, merge, version bump , replacements
    expected_actions = ["tag", "tag", "merge-onto", "create-commit", "create-commit"]
    base_tag = "FIREFOX_BETA_140_BASE"
    end_tag = "FIREFOX_BETA_139_END"
    target_ref = "central"
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
        fetch_files_payload({merge_info["fetch_version_from"]: "139.0b11"}),
        # existing version in `from_branch`
        fetch_files_payload({merge_info["fetch_version_from"]: "140.0a1"}),
        # fetch of original contents of files to bump
        *[fetch_files_payload(iv) for iv in initial_values_by_expected_version.values()],
        # fetch of original contents of `replacements` and `regex_replacements` files
        fetch_files_payload(initial_replacement_values),
        # clobber file
        fetch_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    def assert_func(req):
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
            initial_replacement_values,
            expected_replacement_values,
            end_tag,
            base_tag,
            target_ref,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], assert_func=assert_func)


@pytest.mark.asyncio
async def test_success_beta_to_release(aioresponses, github_installation_responses, context):
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
        "browser/config/version.txt": "136.0",
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
    target_ref = "beta"
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        fetch_files_payload({merge_info["fetch_version_from"]: "135.0"}),
        # existing version in `from_branch`
        fetch_files_payload({merge_info["fetch_version_from"]: "136.0"}),
        # fetch of original contents of files to bump, if we expect any replacements
        fetch_files_payload(initial_values),
        # fetch of original contents of `replacements` and `regex_replacements` files
        fetch_files_payload(initial_replacement_values),
        # clobber file
        fetch_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    def assert_func(req):
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
            initial_replacement_values,
            expected_replacement_values,
            end_tag,
            base_tag,
            target_ref,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], assert_func=assert_func)


@pytest.mark.asyncio
async def test_success_release_to_esr(aioresponses, github_installation_responses, context):
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
    target_ref = "release"
    payload = {
        "actions": ["merge_day"],
        "lando_repo": "repo_name",
        "merge_info": merge_info,
    }

    setup_github_graphql_responses(
        aioresponses,
        # existing version in `to_branch`
        fetch_files_payload({merge_info["fetch_version_from"]: "128.0"}),
        # fetch of original contents of files to bump, if we expect any replacements
        fetch_files_payload(initial_values if expected_bumps else {}),
        # fetch of original contents of `replacements` and `regex_replacements` files
        fetch_files_payload(initial_replacement_values),
        # clobber file
        fetch_files_payload({"CLOBBER": "# Modifying this file will automatically clobber\nMerge day clobber 2025-03-03"}),
    )

    def assert_func(req):
        assert_merge_response(
            context.config["artifact_dir"],
            req,
            expected_actions,
            initial_values,
            expected_bumps,
            initial_replacement_values,
            expected_replacement_bumps,
            end_tag,
            target_ref=target_ref,
        )

    await run_test(aioresponses, github_installation_responses, context, payload, ["merge_day"], assert_func=assert_func)
