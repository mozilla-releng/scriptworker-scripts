# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os

import builddecisionscript.git_push as git_push
import pytest

HOOK_PAYLOAD = {
    "base_ref": None,
    "base_sha": "def456abc123def456abc123def456abc123def4",
    "owner": "dev@example.com",
    "ref": "refs/heads/main",
    "sha": "abc123def456abc123def456abc123def456abc1",
}


@pytest.mark.parametrize(
    "dry_run",
    (
        True,
        False,
    ),
)
def test_build_decision(mocker, dry_run):
    """Add coverage for git_push.build_decision."""
    taskcluster_root_url = "http://taskcluster.local"

    fake_repo = mocker.MagicMock()
    fake_repo.repo_url = "https://github.com/mozilla-releng/fxci-config"
    fake_repo.repo_path = "mozilla-releng/fxci-config"
    fake_task = mocker.MagicMock()

    mocker.patch.object(
        os,
        "environ",
        new={"TASKCLUSTER_ROOT_URL": taskcluster_root_url},
    )
    mock_render = mocker.patch.object(git_push, "render_tc_yml", return_value=fake_task)

    git_push.build_decision(
        repository=fake_repo,
        hook_payload=HOOK_PAYLOAD,
        dry_run=dry_run,
    )

    fake_repo.get_file.assert_called_once_with(
        ".taskcluster.yml",
        revision=HOOK_PAYLOAD["sha"],
    )

    mock_render.assert_called_once()
    render_kwargs = mock_render.call_args[1]
    assert render_kwargs["taskcluster_root_url"] == taskcluster_root_url
    assert render_kwargs["tasks_for"] == "git-push"
    as_slugid = render_kwargs["as_slugid"]
    assert callable(as_slugid)
    # Same name returns the same slugid; different names return different slugids
    assert as_slugid("foo") == as_slugid("foo")
    assert as_slugid("foo") != as_slugid("bar")
    assert render_kwargs["event"] == {
        "ref": "refs/heads/main",
        "before": HOOK_PAYLOAD["base_sha"],
        "after": HOOK_PAYLOAD["sha"],
        "base_ref": None,
        "pusher": {"email": "dev@example.com"},
        "repository": {
            "name": "fxci-config",
            "full_name": "mozilla-releng/fxci-config",
            "html_url": "https://github.com/mozilla-releng/fxci-config",
            "clone_url": "https://github.com/mozilla-releng/fxci-config.git",
        },
    }

    if dry_run:
        fake_task.submit.assert_not_called()
    else:
        fake_task.submit.assert_called_once_with()
