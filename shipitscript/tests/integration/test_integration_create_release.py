from unittest.mock import MagicMock

import shipitscript.ship_actions
import shipitscript.script


def test_create_new_release_hg(context, monkeypatch):
    payload = {
        "product": "firefox",
        "branch": "release",
        "phase": "push",
        "version": "59.0",
        "cron_revision": "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4",
    }

    context.task["payload"] = payload
    ship_it_instance_config = {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some.ship-it.tld/api/root"}
    context.ship_it_instance_config = ship_it_instance_config

    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    get_shippable_revision = MagicMock()
    get_shippable_revision.return_value = "7891011"

    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    attrs = {
        "get_releases.side_effect": [[{"revision": "12345", "build_number": 1}], []],
        "create_new_release.return_value": {"name": "Firefox-59.0-build1"},
    }
    release_instance_mock.configure_mock(**attrs)
    monkeypatch.setattr(shipitscript.ship_actions, "Release_V2", ReleaseClassMock)
    monkeypatch.setattr(shipitscript.ship_actions, "get_shippable_revision", get_shippable_revision)

    shipitscript.script.create_new_release_action(context)

    headers = {"X-Forwarded-Port": "80", "X-Forwarded-Proto": "https"}
    get_shippable_revision.assert_called_with("release", "12345", "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4", None)
    release_instance_mock.create_new_release.assert_called_with("firefox", "release", "59.0", 1, "7891011", None, headers=headers)
    release_instance_mock.trigger_release_phase.assert_called_with("Firefox-59.0-build1", "push", headers=headers)


def test_create_new_release_github(context, monkeypatch):
    payload = {
        "product": "firefox",
        "branch": "release",
        "phase": "push",
        "version": "59.0",
        "cron_revision": "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4",
        "repository_url": "https://github.com/mozilla-mobile/staging-firefox-ios",
    }
    context.task["payload"] = payload
    ship_it_instance_config = {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some.ship-it.tld/api/root"}
    context.ship_it_instance_config = ship_it_instance_config

    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    get_shippable_revision = MagicMock()
    get_shippable_revision.return_value = "7891011"

    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    attrs = {
        "get_releases.side_effect": [[{"revision": "12345", "build_number": 1}], []],
        "create_new_release.return_value": {"name": "Firefox-59.0-build1"},
    }
    release_instance_mock.configure_mock(**attrs)
    monkeypatch.setattr(shipitscript.ship_actions, "Release_V2", ReleaseClassMock)
    monkeypatch.setattr(shipitscript.ship_actions, "get_shippable_revision", get_shippable_revision)

    shipitscript.script.create_new_release_action(context)

    headers = {"X-Forwarded-Port": "80", "X-Forwarded-Proto": "https"}
    get_shippable_revision.assert_called_with(
        "release", "12345", "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4", "https://github.com/mozilla-mobile/staging-firefox-ios"
    )
    release_instance_mock.create_new_release.assert_called_with(
        "firefox", "release", "59.0", 1, "7891011", "https://github.com/mozilla-mobile/staging-firefox-ios", headers=headers
    )
    release_instance_mock.trigger_release_phase.assert_called_with("Firefox-59.0-build1", "push", headers=headers)
