from aiohttp import ClientResponseError
import pytest
from scriptworker.client import TaskVerificationError

from landoscript.errors import LandoscriptError
from landoscript.script import async_main
from landoscript.actions.version_bump import ALLOWED_BUMP_FILES, _VERSION_CLASS_PER_BEGINNING_OF_PATH
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from yarl import URL


def assert_add_commit_response(requests, submit_uri, commit_msg_strings, initial_values, expected_bumps, attempts=1):
    # make sure that exactly one request was made
    # (a single request can add more than one commit, so there should never
    # be a need for more than 1 request)
    assert ("POST", submit_uri) in requests
    reqs = requests[("POST", submit_uri)]
    assert len(reqs) == attempts

    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    req = reqs[0]
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    assert len(req.kwargs["json"]["actions"]) == 1
    action = req.kwargs["json"]["actions"][0]
    assert action["action"] == "create-commit"

    # ensure metadata is correct
    assert action["author"] == "Release Engineering Landoscript <release+landoscript@mozilla.com>"
    # we don't actually verify the value here; it's not worth the trouble of mocking
    assert "date" in action

    # ensure required substrings are in the diff header
    for msg in commit_msg_strings:
        assert msg in action["commitmsg"]

    diffs = action["diff"].split("diff\n")

    # ensure expected bumps are present to a reasonable degree of certainty
    for file, after in expected_bumps.items():
        for diff in diffs:
            # if the version is the last line in the file it may or may not
            # have a trailing newline. either way, there will be one (and
            # only one) in the `-` line of the diff. account for this.
            # the `after` version will only have a newline if the file is
            # intended to have one after the diff has been applied.
            before = initial_values[file].rstrip("\n") + "\n"
            if file in diff and f"\n-{before}+{after}" in diff:
                break
        else:
            assert False, f"no version bump found for {file}: {diffs}"


def assert_status_response(requests, status_uri, attempts=1):
    assert ("GET", status_uri) in requests
    reqs = requests[("GET", status_uri)]
    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    assert len(reqs) == attempts


def setup_test(github_installation_responses, context, payload, repo="repo_name"):
    lando_repo = payload["lando_repo"]
    lando_api = context.config["lando_api"]
    owner = context.config["lando_name_to_github_repo"][lando_repo]["owner"]
    submit_uri = URL(f"{lando_api}/api/v1/{lando_repo}")
    job_id = 12345
    status_uri = URL(f"{lando_api}/push/{job_id}")

    github_installation_responses(owner)

    scopes = [
        f"project:releng:lando:repo:{repo}",
        f"project:releng:lando:action:version_bump",
    ]

    return submit_uri, status_uri, job_id, scopes


def setup_fetch_files_response(aioresponses, code, initial_values={}):
    if initial_values:
        github_response = {}
        for file, contents in initial_values.items():
            github_response[file] = f"{contents}"

        payload = {
            "data": {
                "repository": {k: {"text": v} for k, v in github_response.items()},
            }
        }
    else:
        payload = {}

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=code, payload=payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings",
    (
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "dry_run": True,
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
            id="dryrun",
        ),
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
            id="one_file_new_version",
        ),
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
                "browser/config/version.txt": "134.0\n",
            },
            {
                "browser/config/version.txt": "135.0\n",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="one_file_new_version_retains_newline",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "134.0.1",
                },
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "134.0.1",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="one_file_minor_bump",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "134.0b3",
                },
            },
            {
                "browser/config/version.txt": "134.0b2",
            },
            {
                "browser/config/version.txt": "134.0b3",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="beta_bump_display",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "128.2.1esr",
                },
            },
            {
                "browser/config/version.txt": "128.2.0",
            },
            {
                "browser/config/version.txt": "128.2.1",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="esr_bump",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version_display.txt"],
                    "next_version": "128.2.1esr",
                },
            },
            {
                "browser/config/version_display.txt": "128.2.0esr",
            },
            {
                "browser/config/version_display.txt": "128.2.1esr",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="esr_bump_display",
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
            id="many_files_all_changed",
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
                    "next_version": "135.0b3",
                },
            },
            {
                "browser/config/version.txt": "135.0",
                "browser/config/version_display.txt": "135.0b2",
                "config/milestone.txt": "135.0",
                "mobile/android/version.txt": "135.0b2",
            },
            {
                "browser/config/version_display.txt": "135.0b3",
                "mobile/android/version.txt": "135.0b3",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="many_files_some_changed",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "dontbuild": True,
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release", "DONTBUILD"],
            id="dontbuild_includes_correct_commit_message",
        ),
    ),
)
async def test_success_with_bumps(aioresponses, github_installation_responses, context, payload, initial_values, expected_bumps, commit_msg_strings):
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload)
    setup_fetch_files_response(aioresponses, 200, initial_values)
    dryrun = payload.get("dry_run", False)

    if not dryrun:
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

    assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()
    if not dryrun:
        assert_add_commit_response(aioresponses.requests, submit_uri, commit_msg_strings, initial_values, expected_bumps)
        assert_status_response(aioresponses.requests, status_uri)


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
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload)
    setup_fetch_files_response(aioresponses, 200, initial_values)

    aioresponses.post(submit_uri, status=500)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    aioresponses.get(status_uri, status=202, payload={"status": "pending", "job_id": job_id, "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
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

    assert_add_commit_response(aioresponses.requests, submit_uri, commit_msg_strings, initial_values, expected_bumps, attempts=2)
    assert_status_response(aioresponses.requests, status_uri, attempts=2)
    assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values",
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
                "browser/config/version.txt": "135.0",
            },
            id="one_file_no_change",
        ),
    ),
)
async def test_success_without_bumps(aioresponses, github_installation_responses, context, payload, initial_values):
    submit_uri, status_uri, _, scopes = setup_test(github_installation_responses, context, payload)
    setup_fetch_files_response(aioresponses, 200, initial_values)

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert ("POST", submit_uri) not in aioresponses.requests
    assert ("GET", status_uri) not in aioresponses.requests


@pytest.mark.asyncio
async def test_failure_to_fetch_files(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    _, _, _, scopes = setup_test(github_installation_responses, context, payload)

    # 5 attempts is hardcoded deeper than we can reasonable override it; so
    # just expect it
    for _ in range(5):
        setup_fetch_files_response(aioresponses, 500)

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "couldn't retrieve bump files from github" in e.args[0]


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
    submit_uri, _, _, scopes = setup_test(github_installation_responses, context, payload)
    setup_fetch_files_response(aioresponses, 200, initial_values)

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
    submit_uri, _, _, scopes = setup_test(github_installation_responses, context, payload)
    setup_fetch_files_response(aioresponses, 200, initial_values)
    aioresponses.post(submit_uri, status=202, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "couldn't find status url" in e.args[0]


@pytest.mark.asyncio
async def test_lando_polling_result_not_completed(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload)
    setup_fetch_files_response(aioresponses, 200, initial_values)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=200, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "status is not completed" in e.args[0]


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
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload)
    setup_fetch_files_response(aioresponses, 200, initial_values)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=500, payload={})
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

    assert_status_response(aioresponses.requests, status_uri, attempts=2)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "files,first_bad_file",
    (
        pytest.param(
            ["browser/config/unknown.txt"],
            "browser/config/unknown.txt",
            id="one_file",
        ),
        pytest.param(
            ["browser/config/version.txt", "browser/config/unknown.txt", "foo/bar/baz"],
            "browser/config/unknown.txt",
            id="many_files",
        ),
    ),
)
async def test_bad_bumpfile(github_installation_responses, context, files, first_bad_file):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": files,
            "next_version": "135.0",
        },
    }
    _, _, _, scopes = setup_test(github_installation_responses, context, payload)

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert f"{first_bad_file} is not in version bump allowlist" in e.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scopes,missing",
    (
        pytest.param(
            [
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
            ],
            [
                "project:releng:lando:action:version_bump",
            ],
            id="missing_action_scope",
        ),
        pytest.param(
            [],
            [
                "project:releng:lando:repo:repo_name",
                "project:releng:lando:action:version_bump",
            ],
            id="no_scopes",
        ),
    ),
)
async def test_missing_scopes(context, scopes, missing):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "required scope(s) not present" in e.args[0]
        for m in missing:
            assert m in e.args[0]


def test_no_overlaps_in_version_classes():
    for prefix1 in _VERSION_CLASS_PER_BEGINNING_OF_PATH:
        for prefix2 in _VERSION_CLASS_PER_BEGINNING_OF_PATH:
            if prefix1 == prefix2:
                continue
            assert not prefix2.startswith(prefix1)


def test_all_bump_files_have_version_class():
    for bump_file in ALLOWED_BUMP_FILES:
        assert any([bump_file.startswith(path) for path in _VERSION_CLASS_PER_BEGINNING_OF_PATH])
