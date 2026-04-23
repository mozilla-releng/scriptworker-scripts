# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from builddecisionscript.script import _build_repository, async_main


def test_build_repository_hg(hg_push_task):
    payload = hg_push_task["payload"]
    repo = _build_repository(payload)
    assert repo.repo_url == payload["repoUrl"]
    assert repo.repository_type == "hg"
    assert repo.project == "mozilla-central"
    assert repo.level == "3"
    assert repo.trust_domain == "gecko"
    assert repo.github_token is None


def test_build_repository_fetches_github_token(hg_push_task, mocker):
    payload = hg_push_task["payload"]
    payload["githubTokenSecret"] = "project/releng/github-token"
    mock_get_secret = mocker.patch("builddecisionscript.script.get_secret", return_value="mytoken")

    repo = _build_repository(payload)

    mock_get_secret.assert_called_once_with("project/releng/github-token", secret_key="token")
    assert repo.github_token == "mytoken"


@pytest.mark.asyncio
async def test_async_main_hg_push(hg_push_task, mocker):
    mock_build_decision = mocker.patch("builddecisionscript.hg_push.build_decision")

    await async_main({}, hg_push_task)

    mock_build_decision.assert_called_once()
    call_kwargs = mock_build_decision.call_args.kwargs
    assert call_kwargs["pulse_message"] == hg_push_task["payload"]["pulseMessage"]
    assert call_kwargs["dry_run"] is False
    assert call_kwargs["taskcluster_yml_repo"] is None


@pytest.mark.asyncio
async def test_async_main_hg_push_dry_run(hg_push_task, mocker):
    hg_push_task["payload"]["dryRun"] = True
    mock_build_decision = mocker.patch("builddecisionscript.hg_push.build_decision")

    await async_main({}, hg_push_task)

    call_kwargs = mock_build_decision.call_args.kwargs
    assert call_kwargs["dry_run"] is True


@pytest.mark.asyncio
async def test_async_main_hg_push_with_taskcluster_yml_repo(hg_push_task, mocker):
    hg_push_task["payload"]["taskclusterYmlRepo"] = "https://hg.mozilla.org/other-repo"
    mock_build_decision = mocker.patch("builddecisionscript.hg_push.build_decision")

    await async_main({}, hg_push_task)

    call_kwargs = mock_build_decision.call_args.kwargs
    assert call_kwargs["taskcluster_yml_repo"] is not None
    assert call_kwargs["taskcluster_yml_repo"].repo_url == "https://hg.mozilla.org/other-repo"


@pytest.mark.asyncio
async def test_async_main_hg_push_missing_pulse_message(hg_push_task, mocker):
    del hg_push_task["payload"]["pulseMessage"]
    # schema requires pulseMessage to not be absent, but it's not required by schema
    # the code itself raises ValueError
    mocker.patch("builddecisionscript.hg_push.build_decision")

    with pytest.raises(ValueError, match="pulseMessage is required"):
        await async_main({}, hg_push_task)


@pytest.mark.asyncio
async def test_async_main_cron(cron_task, mocker):
    mock_run = mocker.patch("builddecisionscript.cron.run")

    await async_main({}, cron_task)

    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["branch"] == "default"
    assert call_kwargs["force_run"] is None
    assert call_kwargs["cron_input"] is None
    assert call_kwargs["dry_run"] is False


@pytest.mark.asyncio
async def test_async_main_cron_with_options(cron_task, mocker):
    cron_task["payload"]["forceRun"] = "nightly"
    cron_task["payload"]["cronInput"] = {"key": "val"}
    cron_task["payload"]["dryRun"] = True
    mock_run = mocker.patch("builddecisionscript.cron.run")

    await async_main({}, cron_task)

    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["force_run"] == "nightly"
    assert call_kwargs["cron_input"] == {"key": "val"}
    assert call_kwargs["dry_run"] is True
