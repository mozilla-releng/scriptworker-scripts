from unittest.mock import MagicMock


import shipitscript.ship_actions
import shipitscript.script
import mozilla_repo_urls


def test_create_new_release_hg(context, monkeypatch):
    payload = {
        "product": "firefox",
        "branch": "release",
        "phase": "push",
        "version": "59.0",
        "cron_revision": "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4",
    }

    task = {
        "metadata": {
            "source": "https://hg.mozilla.org/releases/mozilla-beta/file/8a2c52b9488e5ae5a8dc8500d3430d5ebe3d9a85/taskcluster/kinds/maybe-release",
        },
        "payload": payload,
    }

    context.task = task
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
        "release",
        "12345",
        "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4",
        mozilla_repo_urls.parse("https://hg.mozilla.org/releases/mozilla-beta/file/8a2c52b9488e5ae5a8dc8500d3430d5ebe3d9a85/taskcluster/kinds/maybe-release"),
    )
    release_instance_mock.create_new_release.assert_called_with("firefox", "release", "59.0", 1, "7891011", None, headers=headers)
    release_instance_mock.trigger_release_phase.assert_called_with("Firefox-59.0-build1", "push", headers=headers)


def test_create_new_release_github(context, monkeypatch):
    payload = {
        "product": "firefox",
        "branch": "release",
        "phase": "push",
        "version": "59.0",
        "cron_revision": "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4",
    }

    task_source_url = "https://github.com/mozilla-mobile/staging-firefox-ios/blob/9cf3242b9ba58f161a4401a6eaf0a2f5ca0dbacc/taskcluster/kinds/beta-releases"
    task = {
        "metadata": {
            "source": task_source_url,
        },
        "payload": payload,
    }
    context.task = task
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
        "release",
        "12345",
        "5e37f358c4cc77de5e140b82e89e2f0c7be5c2a4",
        mozilla_repo_urls.parse(
            "https://github.com/mozilla-mobile/staging-firefox-ios/blob/9cf3242b9ba58f161a4401a6eaf0a2f5ca0dbacc/taskcluster/kinds/beta-releases"
        ),
    )
    release_instance_mock.create_new_release.assert_called_with(
        "firefox", "release", "59.0", 1, "7891011", "https://github.com/mozilla-mobile/staging-firefox-ios", headers=headers
    )
    release_instance_mock.trigger_release_phase.assert_called_with("Firefox-59.0-build1", "push", headers=headers)
