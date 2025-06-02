import os
from unittest.mock import MagicMock, patch

import pytest
from scriptworker import artifacts, client
from scriptworker.context import Context
from scriptworker.exceptions import TaskVerificationError

import pushapkscript
from pushapkscript import jarsigner, manifest, publish, task
from pushapkscript.exceptions import ConfigValidationError
from pushapkscript.script import _get_product_config, _log_warning_forewords, async_main, get_default_config, main

from .helpers.mock_file import mock_open


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "android_product, upstream_artifacts, is_aab, raises",
    (
        ("beta", {"someTaskId": ["/some/path/to/one.apk", "/some/path/to/another.apk"], "someOtherTaskId": ["/some/path/to/yet_another.apk"]}, False, False),
        ("release", {"someTaskId": ["/some/path/to/one.apk", "/some/path/to/another.apk"], "someOtherTaskId": ["/some/path/to/yet_another.apk"]}, False, False),
        ("dep", {"someTaskId": ["/some/path/to/one.aab", "/some/path/to/another.aab"], "someOtherTaskId": ["/some/path/to/yet_another.aab"]}, True, False),
        ("focus", {"someTaskId": ["/some/path/to/one.aab", "/some/path/to/another.aab"], "someOtherTaskId": ["/some/path/to/yet_another.aab"]}, True, False),
        ("aurora", {"someTaskId": ["/some/path/to/one.aab", "/some/path/to/another.aab"], "someOtherTaskId": ["/some/path/to/yet_another.apk"]}, True, True),
    ),
)
async def test_async_main(monkeypatch, android_product, upstream_artifacts, is_aab, raises):
    monkeypatch.setattr(
        artifacts,
        "get_upstream_artifacts_full_paths_per_task_id",
        lambda _: (upstream_artifacts, {}),
    )
    monkeypatch.setattr(jarsigner, "verify", lambda _, __, ___: None)
    monkeypatch.setattr(manifest, "verify", lambda _, __: None)
    monkeypatch.setattr(task, "extract_android_product_from_scopes", lambda _: android_product)
    monkeypatch.setattr(
        pushapkscript.script,
        "_get_product_config",
        lambda _, __: {
            "apps": {
                android_product: {
                    "package_names": [android_product],
                    "certificate_alias": android_product,
                    "google": {"default_track": "beta", "credentials_file": "{}.json".format(android_product)},
                }
            }
        },
    )

    context = MagicMock()
    context.config = {"do_not_contact_google_play": True}
    context.task = {"payload": {"channel": android_product}}

    if is_aab:

        async def assert_google_play_call_aab(_, __, all_aabs_files, ___):
            assert sorted([file.name for file in all_aabs_files]) == ["/some/path/to/another.aab", "/some/path/to/one.aab", "/some/path/to/yet_another.aab"]

        monkeypatch.setattr(publish, "publish_aab", assert_google_play_call_aab)
    else:

        async def assert_google_play_call_apk(_, __, all_apks_files, ___):
            assert sorted([file.name for file in all_apks_files]) == ["/some/path/to/another.apk", "/some/path/to/one.apk", "/some/path/to/yet_another.apk"]

        monkeypatch.setattr(publish, "publish", assert_google_play_call_apk)

    if raises:
        with patch("pushapkscript.script.open", new=mock_open):
            with pytest.raises(TaskVerificationError):
                await async_main(context)
    else:
        with patch("pushapkscript.script.open", new=mock_open):
            await async_main(context)


def test_get_product_config_validation():
    context = Context()
    context.config = {}

    with pytest.raises(ConfigValidationError):
        _get_product_config(context, "fenix")


def test_get_product_config_unknown_product():
    context = Context()
    context.config = {"products": [{"product_names": ["fenix"]}]}

    with pytest.raises(TaskVerificationError):
        _get_product_config(context, "unknown")


def test_get_product_config():
    context = Context()
    context.config = {"products": [{"product_names": ["fenix"], "foo": "bar"}]}

    assert _get_product_config(context, "fenix") == {"product_names": ["fenix"], "foo": "bar"}


@pytest.mark.parametrize(
    "is_allowed_to_push, dry_run, target_store, expected",
    (
        (
            True,
            False,
            "google",
            "You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.",
        ),
        (True, True, "google", "APKs will be submitted, but no change will not be committed."),
        (False, True, "google", "This pushapk instance is not allowed to talk to Google Play. *All* requests will be mocked."),
        (False, False, "google", "This pushapk instance is not allowed to talk to Google Play. *All* requests will be mocked."),
    ),
)
def test_log_warning_forewords(caplog, monkeypatch, is_allowed_to_push, dry_run, target_store, expected):
    _log_warning_forewords(is_allowed_to_push, dry_run, target_store)
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert expected in caplog.text


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    assert get_default_config() == {
        "work_dir": os.path.join(parent_dir, "work_dir"),
        "schema_file": os.path.join(os.path.dirname(pushapkscript.__file__), "data/pushapk_task_schema.json"),
        "verbose": False,
    }


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(client, "sync_main", sync_main_mock)
    main()
    sync_main_mock.asset_called_once_with(async_main, default_config=get_default_config())
