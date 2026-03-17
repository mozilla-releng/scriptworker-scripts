import pytest
from scriptworker.exceptions import TaskVerificationError

from pushflatpakscript.task import get_flatpak_app, get_flatpak_channel, is_allowed_to_push_to_flathub


def test_get_flatpak_channel_without_payload_raises():
    task = {"payload": {}}
    config = {}
    with pytest.raises(TaskVerificationError):
        get_flatpak_channel(config, task)


@pytest.mark.parametrize("raises, channel", ((False, "stable"), (False, "beta"), (False, "mock"), (False, "beta"), (False, "beta"), (True, "bogus")))
def test_get_flatpak_channel_dep(raises, channel):
    task = {"scopes": [], "payload": {"channel": channel}}
    config = {"app_id": "org.mozilla.firefox", "taskcluster_scope_prefix": "project:releng:flathub:firefox:", "push_to_flathub": False}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_flatpak_channel(config, task)
    else:
        assert get_flatpak_channel(config, task) == channel


@pytest.mark.parametrize(
    "raises, scopes, channel",
    (
        (False, ["project:releng:flathub:firefox:stable"], "stable"),
        (False, ["project:releng:flathub:firefox:beta"], "beta"),
        (False, ["project:releng:flathub:firefox:mock"], "mock"),
        (False, ["project:releng:flathub:firefox:beta", "some:other:scope"], "beta"),
        (False, ["project:releng:flathub:firefox:beta", "project:releng:flathub:firefox:stable"], "beta"),
        (True, ["project:releng:flathub:firefox:stable"], "beta"),
        (False, ["project:releng:flathub:firefox:stable:org.mozilla.firefox"], "stable"),
        (False, ["project:releng:flathub:firefox:beta:org.mozilla.firefox"], "beta"),
        (False, ["project:releng:flathub:firefox:mock:org.mozilla.firefox"], "mock"),
        (False, ["project:releng:flathub:firefox:beta:org.mozilla.firefox", "some:other:scope"], "beta"),
        (False, ["project:releng:flathub:firefox:beta:org.mozilla.firefox", "project:releng:flathub:firefox:stable:org.mozilla.firefox"], "beta"),
        (True, ["project:releng:flathub:firefox:stable:org.mozilla.firefox"], "beta"),
        (False, ["project:releng:flathub:firefox:beta:org.mozilla.firefox", "project:releng:flathub:firefox:beta:org.mozilla.thunderbird"], "beta"),
    ),
)
def test_get_flatpak_channel_prod(raises, scopes, channel):
    task = {"scopes": scopes, "payload": {"channel": channel}}
    config = {"app_id": "org.mozilla.firefox", "taskcluster_scope_prefix": "project:releng:flathub:firefox:", "push_to_flathub": True}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_flatpak_channel(config, task)
    else:
        assert get_flatpak_channel(config, task) == channel


@pytest.mark.parametrize(
    "channel, push_to_flathub, expected",
    (
        ("beta", True, True),
        ("stable", True, True),
        ("beta", False, False),
        ("stable", False, False),
        ("mock", True, False),
        ("mock", False, False),
    ),
)
def test_is_allowed_to_push_to_flathub(channel, push_to_flathub, expected):
    config = {"app_id": "org.mozilla.firefox", "taskcluster_scope_prefix": "project:releng:flathub:firefox:", "push_to_flathub": push_to_flathub}
    assert is_allowed_to_push_to_flathub(config, channel) == expected


@pytest.mark.parametrize(
    "raises, scopes, channel, expected",
    (
        (False, ["project:releng:flathub:firefox:stable"], "stable", "org.mozilla.firefox"),
        (False, ["project:releng:flathub:firefox:stable:org.mozilla.firefox_nightly"], "stable", "org.mozilla.firefox_nightly"),
        (False, ["project:releng:flathub:firefox:beta:org.mozilla.firefox_nightly"], "stable", "org.mozilla.firefox"),
        (True, ["project:releng:flathub:firefox:stable:org.mozilla.firefox", "project:releng:flathub:firefox:stable:org.mozilla.firefox_nightly"], "stable", None),
    ),
)
def test_get_flatpak_app(raises, scopes, channel, expected):
    config = {"app_id": "org.mozilla.firefox", "taskcluster_scope_prefix": "project:releng:flathub:firefox:", "push_to_flathub": True}
    task = {"scopes": scopes, "payload": {"channel": channel}}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_flatpak_app(config, task)
    else:
        assert get_flatpak_app(config, task) == expected
