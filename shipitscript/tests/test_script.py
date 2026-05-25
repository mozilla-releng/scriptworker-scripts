import os
from unittest.mock import MagicMock

import pytest
from scriptworker import client
from scriptworker.exceptions import ScriptWorkerTaskException

import shipitscript
from shipitscript import script, ship_actions


@pytest.mark.parametrize("scopes", (["project:releng:ship-it:action:mark-as-shipped", "project:releng:ship-it:server:dev"],))
@pytest.mark.asyncio
async def test_mark_as_shipped(context, monkeypatch, scopes):
    context.task["scopes"] = scopes

    mark_as_shipped_v2_mock = MagicMock()
    monkeypatch.setattr(ship_actions, "mark_as_shipped_v2", mark_as_shipped_v2_mock)

    await script.async_main(context)
    mark_as_shipped_v2_mock.assert_called_with(
        {
            "scope": scopes[-1],
            "api_root_v2": "http://some-ship-it.url/v2",
            "timeout_in_seconds": 1,
            "taskcluster_client_id": "some-id",
            "taskcluster_access_token": "some-token",
        },
        "Firefox-59.0b3-build1",
    )


@pytest.mark.parametrize("scopes", (["project:releng:ship-it:action:mark-as-merged", "project:releng:ship-it:server:dev"],))
@pytest.mark.asyncio
async def test_mark_as_merged(context, monkeypatch, scopes):
    context.task["scopes"] = scopes
    context.task["payload"] = {"automation_id": 123}

    mark_as_merged_mock = MagicMock()
    monkeypatch.setattr(ship_actions, "mark_as_merged", mark_as_merged_mock)

    await script.async_main(context)
    mark_as_merged_mock.assert_called_with(
        {
            "scope": scopes[-1],
            "api_root_v2": "http://some-ship-it.url/v2",
            "timeout_in_seconds": 1,
            "taskcluster_client_id": "some-id",
            "taskcluster_access_token": "some-token",
        },
        123,
    )


@pytest.mark.parametrize(
    "task,raises",
    (
        (
            {
                "dependencies": ["someTaskId"],
                "payload": {"release_name": "Firefox-59.0b3-build1"},
                "scopes": ["project:releng:ship-it:server:dev", "project:releng:ship-it:action:mark-as-shipped"],
            },
            False,
        ),
        (
            {
                "dependencies": ["someTaskId"],
                "payload": {
                    "release_name": "Firefox-59.0b3-build1",
                    "product": "Firefox",
                    "version": "61.0b8",
                    "revision": "aadufhgdgf54g89dfngjerhtirughdfg",
                    "branch": "maple",
                    "build_number": 1,
                },
                "scopes": ["project:releng:ship-it:server:dev"],
            },
            True,
        ),
    ),
)
@pytest.mark.asyncio
async def test_async_main(context, monkeypatch, task, raises):
    context.task = task

    mark_as_shipped_v2_mock = MagicMock()
    monkeypatch.setattr(ship_actions, "mark_as_shipped_v2", mark_as_shipped_v2_mock)

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            await script.async_main(context)
    else:
        await script.async_main(context)


@pytest.mark.parametrize(
    "existing_nightly,expect_create,expect_exit",
    (
        # no existing nightly: create one
        (None, True, False),
        # existing nightly matches version + locales: no-op
        ([{"version": "150.0a1", "locales": ["en-US", "de"]}], False, False),
        # existing nightly mismatches version: sys.exit(1)
        ([{"version": "149.0a1", "locales": ["en-US", "de"]}], False, True),
        # existing nightly mismatches locales: sys.exit(1)
        ([{"version": "150.0a1", "locales": ["en-US"]}], False, True),
    ),
)
def test_create_new_nightly_release_action(context, monkeypatch, existing_nightly, expect_create, expect_exit):
    context.ship_it_instance_config = context.config["shipit_instance"]
    context.task["payload"] = {
        "product": "firefox",
        "channel": "nightly",
        "buildid": "20260525000000",
        "version": "150.0a1",
        "locales": ["en-US", "de"],
    }

    get_nightly_metadata_mock = MagicMock(return_value=existing_nightly)
    create_new_nightly_release_mock = MagicMock()
    monkeypatch.setattr(ship_actions, "get_nightly_metadata", get_nightly_metadata_mock)
    monkeypatch.setattr(ship_actions, "create_new_nightly_release", create_new_nightly_release_mock)

    if expect_exit:
        with pytest.raises(SystemExit):
            script.create_new_nightly_release_action(context)
    else:
        script.create_new_nightly_release_action(context)

    get_nightly_metadata_mock.assert_called_with(context.ship_it_instance_config, "firefox", "nightly", "20260525000000")
    if expect_create:
        create_new_nightly_release_mock.assert_called_with(
            context.ship_it_instance_config, "firefox", "nightly", "20260525000000", "150.0a1", ["en-US", "de"]
        )
    else:
        create_new_nightly_release_mock.assert_not_called()


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    data_dir = os.path.join(os.path.dirname(shipitscript.__file__), "data")
    assert script.get_default_config() == {
        "work_dir": os.path.join(parent_dir, "work_dir"),
        "verbose": False,
        "mark_as_shipped_schema_file": os.path.join(data_dir, "mark_as_shipped_task_schema.json"),
        "mark_as_merged_schema_file": os.path.join(data_dir, "mark_as_merged_task_schema.json"),
        "create_new_release_schema_file": os.path.join(data_dir, "create_new_release_task_schema.json"),
        "create_new_nightly_release_schema_file": os.path.join(data_dir, "create_new_nightly_release_task_schema.json"),
    }


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(client, "sync_main", sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())
