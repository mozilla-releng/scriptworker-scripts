import datetime
import json
from pathlib import Path
from yarl import URL
from pytest_scriptworker_client import get_files_payload

import pytest
from scriptworker.context import Context
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT

from landoscript.script import async_main

pytest_plugins = ("pytest-scriptworker-client",)

here = Path(__file__).parent


@pytest.fixture(scope="function")
def context(privkey_file, tmpdir):
    context = Context()
    context.config = {
        "artifact_dir": tmpdir,
        "lando_api": "https://lando.fake/api",
        "lando_token": "super secret",
        "github_config": {
            "app_id": 12345,
            "privkey_file": privkey_file,
        },
        "poll_time": 0,
        "sleeptime_callback": lambda _: 0,
        "treestatus_url": "https://treestatus.fake",
    }

    return context


@pytest.fixture(scope="session")
def datadir():
    return here / "data"


@pytest.fixture(scope="session")
def privkey_file(datadir):
    return datadir / "test_private_key.pem"


@pytest.fixture(scope="function")
def patch_date(monkeypatch):
    def inner(location, year, month, day):
        class mydate(datetime.date):
            @classmethod
            def today(cls):
                return datetime.date(year, month, day)

        monkeypatch.setattr(location, "date", mydate)

    return inner


def setup_treestatus_response(aioresponses, context, tree="repo_name", status="approval required", has_err=False):
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


def setup_test(aioresponses, github_installation_responses, context, payload, actions, repo="repo_name"):
    lando_repo = payload["lando_repo"]
    lando_api = context.config["lando_api"]
    owner = "faker"
    repo_info_uri = URL(f"{lando_api}/repoinfo/{repo}")
    submit_uri = URL(f"{lando_api}/repo/{lando_repo}")
    job_id = 12345
    status_uri = URL(f"{lando_api}/job/{job_id}")

    aioresponses.get(
        repo_info_uri,
        status=200,
        payload={
            "repo_url": f"https://github.com/{owner}/{repo}",
            "branch_name": "fake_branch",
            "scm_level": "whatever",
        },
    )

    github_installation_responses(owner)

    scopes = [f"project:releng:lando:repo:{repo}"]
    for action in actions:
        scopes.append(f"project:releng:lando:action:{action}")

    return submit_uri, status_uri, job_id, scopes


async def run_test(
    aioresponses, github_installation_responses, context, payload, actions, should_submit=True, assert_func=None, repo="repo_name", err=None, errmsg=""
):
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, actions, repo)

    if should_submit:
        aioresponses.post(
            submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"}
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

    # error cases and success cases are different enough that it's clearer to call
    # `async_main` in different blocks than try to account for them both in one block.
    if err:
        try:
            await async_main(context)
            assert False, f"should've raised {err}"
        except Exception as e:
            assert isinstance(e, err)
            if errmsg is not None:
                assert errmsg in e.args[0]
    else:
        await async_main(context)
        if should_submit:
            req = assert_lando_submission_response(aioresponses.requests, submit_uri)
            assert_status_response(aioresponses.requests, status_uri)
            if assert_func:
                assert_func(req)
        else:
            assert ("POST", submit_uri) not in aioresponses.requests
            assert ("GET", status_uri) not in aioresponses.requests


def setup_github_graphql_responses(aioresponses, *payloads):
    for payload in payloads:
        aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload=payload)


def setup_l10n_file_responses(aioresponses, l10n_bump_info, initial_values, expected_locales):
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

    setup_github_graphql_responses(aioresponses, get_files_payload(file_responses))


def assert_lando_submission_response(requests, submit_uri, attempts=1):
    assert ("POST", submit_uri) in requests
    reqs = requests[("POST", submit_uri)]
    assert len(reqs) == attempts
    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    assert "Authorization" in reqs[0].kwargs["headers"]
    assert reqs[0].kwargs["headers"]["Authorization"] == "Bearer super secret"
    assert reqs[0].kwargs["headers"]["User-Agent"] == "Lando-User/release+landoscript@mozilla.com"
    return reqs[0]


def assert_status_response(requests, status_uri, attempts=1):
    assert ("GET", status_uri) in requests
    reqs = requests[("GET", status_uri)]
    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    assert len(reqs) == attempts
    assert "Authorization" in reqs[0].kwargs["headers"]
    assert reqs[0].kwargs["headers"]["Authorization"] == "Bearer super secret"
    assert reqs[0].kwargs["headers"]["User-Agent"] == "Lando-User/release+landoscript@mozilla.com"


def assert_tag_response(req, tag_info, target_revision):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    tag_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "tag"]
    assert len(tag_actions) == len(tag_info["tags"])

    requested_tags = set([action["name"] for action in tag_actions])
    assert requested_tags == set(tag_info["tags"])

    revisions = set([action["target"] for action in tag_actions])
    assert len(revisions) == 1
    assert revisions.pop() == target_revision


def assert_add_commit_response(action, commit_msg_strings, initial_values, expected_bumps, mode=None):
    # ensure metadata is correct
    assert action["author"] == "Release Engineering Landoscript <release+landoscript@mozilla.com>"
    # we don't actually verify the value here; it's not worth the trouble of mocking
    assert "date" in action

    # ensure required substrings are in the diff header
    for msg in commit_msg_strings:
        assert msg in action["commitmsg"]

    diffs = action["diff"].split("\ndiff")

    # Extract file paths from diffs and verify they are sorted
    file_paths = []
    for i, diff in enumerate(diffs):
        if not diff:
            continue

        if i == 0:
            path_line = diff.split("\n")[0]
        else:
            path_line = "diff" + diff.split("\n")[0]

        file_path = path_line.split(" ")[2][2:]
        file_paths.append(file_path)

    assert file_paths == sorted(file_paths), f"Files in diff are not sorted. Got: {file_paths}"

    # ensure expected bumps are present to a reasonable degree of certainty
    for file, after in expected_bumps.items():
        for diff in diffs:
            if initial_values[file] is None:
                before = None
            else:
                before = initial_values[file]
            if file in diff:
                # any expected changes that are multiline files do not have
                # their diffs checked in depth; it's not worth the effort to
                # do so. we've already checked that there was _some_ change in
                # the diff.
                if not before:
                    # addition
                    assert f"new file mode {mode or 100644}" in diff
                    if "\n" not in after and f"+{after}" in diff:
                        break
                elif not after:
                    # removal
                    assert f"deleted file mode {mode or 100644}" in diff
                    if not "\n" in before and f"-{before}" in diff:
                        break
                else:
                    # change
                    if "\n" in before or "\n" in after:
                        break

                    if f"-{before}" in diff and f"+{after}" in diff:
                        break
        else:
            assert False, f"no bump found for {file}: {diffs}"


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


def assert_l10n_bump_response(req, l10n_bump_info, expected_changes, initial_values, expected_values, dontbuild=False, ignore_closed_tree=True):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]

    # when l10n bump is being down as part of something else, eg: merge day
    # there may be create-commit actions that are unrelated to l10n
    l10n_create_commit_actions = {}
    for lbi in l10n_bump_info:
        name = lbi["name"]

        for cca in create_commit_actions:
            if name in cca["commitmsg"]:
                l10n_create_commit_actions[name] = cca

    for lbi in l10n_bump_info:
        name = lbi["name"]
        action = l10n_create_commit_actions.get(name)

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


def assert_merge_response(
    artifact_dir,
    req,
    expected_actions,
    initial_values,
    expected_bumps,
    initial_replacement_values={},
    expected_replacement_bumps={},
    end_tag="",
    end_tag_target_ref="",
    base_tag="",
    base_tag_target_ref="",
    target_ref="",
):
    actions = req.kwargs["json"]["actions"]
    action_names = [action["action"] for action in actions]
    assert action_names == expected_actions

    tag_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "tag"]
    if base_tag:
        assert len(tag_actions) == 2
        # if it exists, base tag happens second
        assert tag_actions[0]["name"] == end_tag
        assert tag_actions[0]["target"] == end_tag_target_ref
        assert tag_actions[1]["name"] == base_tag
        assert tag_actions[1]["target"] == base_tag_target_ref
    elif end_tag:
        assert len(tag_actions) == 1
        assert tag_actions[0]["name"] == end_tag
        assert tag_actions[0]["target"] == end_tag_target_ref

    if "merge-onto" in expected_actions:
        # `merge-onto` action w/ target revision, commit message, and `ours` strategy
        merge_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "merge-onto"]
        assert len(merge_actions) == 1
        action = merge_actions[0]
        assert action["target"] == target_ref
        assert action["strategy"] == "theirs"
        assert "commit_message" in action

    # `create-commit` action. check diff for:
    # - firefox version bumps
    create_commit_actions = iter(
        [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit" and "l10n changesets" not in action["commitmsg"]]
    )
    if expected_bumps:
        assert (artifact_dir / "public/build/version-bump.diff").exists()

        action = next(create_commit_actions)

        commit_msg_strings = ["Automatic version bump", "CLOSED TREE"]
        assert_add_commit_response(action, commit_msg_strings, initial_values, expected_bumps)

    # - `replacements` bumps
    # - `regex-replacements` bumps
    # - CLOBBER
    if expected_replacement_bumps:
        assert (artifact_dir / "public/build/replacements.diff").exists()

        action = next(create_commit_actions)

        commit_msg_strings = ["Update configs", "a=release", "IGNORE BROKEN CHANGESETS", "CLOSED TREE"]
        assert_add_commit_response(action, commit_msg_strings, initial_replacement_values, expected_replacement_bumps)
