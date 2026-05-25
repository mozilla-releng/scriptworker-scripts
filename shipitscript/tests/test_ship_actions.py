from unittest.mock import MagicMock

import pytest

import shipitscript.ship_actions


@pytest.mark.parametrize("timeout, expected_timeout", ((1, 1), ("10", 10), (None, 60)))
def test_mark_as_shipped_v2(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    release_info = {"status": "shipped"}
    attrs = {"getRelease.return_value": release_info}
    release_instance_mock.configure_mock(**attrs)
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitscript.ship_actions, "Release_V2", ReleaseClassMock)

    ship_it_instance_config = {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some.ship-it.tld/api/root"}
    if timeout is not None:
        ship_it_instance_config["timeout_in_seconds"] = timeout
    release_name = "Firefox-59.0b1-build1"

    shipitscript.ship_actions.mark_as_shipped_v2(ship_it_instance_config, release_name)

    ReleaseClassMock.assert_called_with(
        taskcluster_client_id="some-id", taskcluster_access_token="some-token", api_root="http://some.ship-it.tld/api/root", timeout=expected_timeout
    )
    release_instance_mock.update_status.assert_called_with(
        "Firefox-59.0b1-build1", status="shipped", headers={"X-Forwarded-Proto": "https", "X-Forwarded-Port": "80"}
    )


@pytest.mark.parametrize("timeout, expected_timeout", ((1, 1), ("10", 10), (None, 60)))
def test_mark_as_merged(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitscript.ship_actions, "Release_V2", ReleaseClassMock)

    ship_it_instance_config = {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some.ship-it.tld/api/root"}
    if timeout is not None:
        ship_it_instance_config["timeout_in_seconds"] = timeout
    automation_id = 123

    shipitscript.ship_actions.mark_as_merged(ship_it_instance_config, automation_id)

    ReleaseClassMock.assert_called_with(
        taskcluster_client_id="some-id", taskcluster_access_token="some-token", api_root="http://some.ship-it.tld/api/root", timeout=expected_timeout
    )
    release_instance_mock.complete_merge_automation.assert_called_with(123, headers={"X-Forwarded-Proto": "https", "X-Forwarded-Port": "80"})


@pytest.mark.parametrize("timeout, expected_timeout", ((1, 1), ("10", 10), (None, 60)))
def test_get_nightly_metadata(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    nightly_metadata = [{"version": "150.0a1", "locales": ["en-US", "de"]}]
    attrs = {"get_nightly_metadata.return_value": nightly_metadata}
    release_instance_mock.configure_mock(**attrs)
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitscript.ship_actions, "Release_V2", ReleaseClassMock)

    ship_it_instance_config = {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some.ship-it.tld/api/root"}
    if timeout is not None:
        ship_it_instance_config["timeout_in_seconds"] = timeout

    ret = shipitscript.ship_actions.get_nightly_metadata(ship_it_instance_config, "firefox", "nightly", "20260525000000")

    ReleaseClassMock.assert_called_with(
        taskcluster_client_id="some-id", taskcluster_access_token="some-token", api_root="http://some.ship-it.tld/api/root", timeout=expected_timeout
    )
    release_instance_mock.get_nightly_metadata.assert_called_with(
        "firefox", "nightly", "20260525000000", headers={"X-Forwarded-Proto": "https", "X-Forwarded-Port": "80"}
    )


@pytest.mark.parametrize("timeout, expected_timeout", ((1, 1), ("10", 10), (None, 60)))
def test_create_new_nightly_release(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    attrs = {"create_new_nightly_release.return_value": {"message": "ok"}}
    release_instance_mock.configure_mock(**attrs)
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitscript.ship_actions, "Release_V2", ReleaseClassMock)

    ship_it_instance_config = {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some.ship-it.tld/api/root"}
    if timeout is not None:
        ship_it_instance_config["timeout_in_seconds"] = timeout

    shipitscript.ship_actions.create_new_nightly_release(
        ship_it_instance_config, "firefox", "nightly", "20260525000000", "150.0a1", ["en-US", "de"]
    )

    ReleaseClassMock.assert_called_with(
        taskcluster_client_id="some-id", taskcluster_access_token="some-token", api_root="http://some.ship-it.tld/api/root", timeout=expected_timeout
    )
    release_instance_mock.create_new_nightly_release.assert_called_with(
        "firefox", "nightly", "20260525000000", "150.0a1", ["en-US", "de"], headers={"X-Forwarded-Proto": "https", "X-Forwarded-Port": "80"}
    )
