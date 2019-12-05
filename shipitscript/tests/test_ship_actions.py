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
