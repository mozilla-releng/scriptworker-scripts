import pytest
from scriptworker.exceptions import TaskVerificationError

from pushflatpakscript.task import get_flatpak_channel, is_allowed_to_push_to_flathub


def test_get_flatpak_channel_without_payload_raises():
    task = {"payload": {}}
    config = {}
    with pytest.raises(TaskVerificationError):
        get_flatpak_channel(config, task)


@pytest.mark.parametrize("raises, channel", ((False, "stable"), (False, "beta"), (False, "mock"), (False, "beta"), (False, "beta"), (True, "bogus")))
def test_get_flatpak_channel_dep(raises, channel):
    task = {"scopes": [], "payload": {"channel": channel}}
    config = {"push_to_flathub": False}
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
    ),
)
def test_get_flatpak_channel_prod(raises, scopes, channel):
    pass  # TODO: revert this
    # task = {"scopes": scopes, "payload": {"channel": channel}}
    # config = {"push_to_flathub": True}
    # if raises:
        # with pytest.raises(TaskVerificationError):
            # get_flatpak_channel(config, task)
    # else:
        # assert get_flatpak_channel(config, task) == channel


@pytest.mark.parametrize(
    "channel, push_to_flathub, expected",
    (("beta", True, True), ("stable", True, True), ("beta", False, False), ("stable", False, False), ("mock", True, False), ("mock", False, False),),
)
def test_is_allowed_to_push_to_flathub(channel, push_to_flathub, expected):
    config = {"push_to_flathub": push_to_flathub}
    assert is_allowed_to_push_to_flathub(config, channel) == expected
