import os
from asyncio import Future
from contextlib import nullcontext as does_not_raise
from inspect import iscoroutine

import pytest

from unittest.mock import AsyncMock

import bitrisescript.script as script
from scriptworker_client.exceptions import TaskVerificationError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "task, expectation, expected_num_futures",
    (
        pytest.param({"scopes": ["test:prefix:app:bar"]}, pytest.raises(TaskVerificationError), 0, id="no_workflow"),
        pytest.param({"scopes": ["test:prefix:app:bar", "test:prefix:workflow:baz"]}, does_not_raise(), 1, id="single_workflow"),
        pytest.param({"scopes": ["test:prefix:app:bar", "test:prefix:workflow:baz", "test:prefix:workflow:other"]}, does_not_raise(), 2, id="two_workflows"),
        pytest.param({"scopes": ["bad:app:bar"]}, pytest.raises(TaskVerificationError), 0, id="invalid_prefix_app"),
        pytest.param({"scopes": ["test:prefix:app:bar", "bad:workflow:baz"]}, pytest.raises(TaskVerificationError), 0, id="invalid_prefix_workflow"),
    ),
)
async def test_async_main(mocker, config, task, expectation, expected_num_futures):
    # Mock out the client
    client_mock = mocker.Mock()
    client_mock.configure_mock(
        **{
            "close.return_value": Future(),
            "set_auth.return_value": None,
            "set_app_prefix.return_value": Future(),
        }
    )
    client_mock.close.return_value.set_result(None)
    client_mock.set_app_prefix.return_value.set_result(None)
    mocker.patch("bitrisescript.script.BitriseClient", return_value=client_mock)

    # Mock out asyncio.gather
    mock_gather = mocker.patch("bitrisescript.script.asyncio.gather", return_value=Future())
    mock_gather.return_value.set_result(None)

    async_mock = AsyncMock()
    mocker.patch("bitrisescript.script.get_running_builds", side_effect=async_mock)
    async_mock.return_value = []

    task_def = {
        "scopes": [],
        "payload": {
            "build_params": {},
        },
    }
    task_def.update(task)

    with expectation:
        await script.async_main(config, task_def)

        args = mock_gather.call_args.args
        assert mock_gather.call_count == 1
        assert all(iscoroutine(a) for a in args)
        assert len(args) == expected_num_futures


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    assert script.get_default_config() == {
        "work_dir": os.path.join(parent_dir, "work_dir"),
        "verbose": False,
    }


def test_main(mocker, monkeypatch):
    sync_main_mock = mocker.MagicMock()
    monkeypatch.setattr(script, "sync_main", sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())
