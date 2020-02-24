import pytest
from scriptworker.exceptions import TaskVerificationError

from pushsnapscript.task import get_snap_channel, is_allowed_to_push_to_snap_store


def test_get_snap_channel_without_payload_raises():
    task = {"payload": {}}
    config = {}
    with pytest.raises(TaskVerificationError):
        get_snap_channel(config, task)


@pytest.mark.parametrize(
    "raises, channel", ((False, "candidate"), (False, "beta"), (False, "esr/stable"), (False, "mock"), (False, "beta"), (False, "beta"), (True, "bogus"))
)
def test_get_snap_channel_dep(raises, channel):
    task = {"scopes": [], "payload": {"channel": channel}}
    config = {"push_to_store": False}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_snap_channel(config, task)
    else:
        assert get_snap_channel(config, task) == channel


@pytest.mark.parametrize(
    "raises, scopes, channel",
    (
        (False, ["project:releng:snapcraft:firefox:candidate"], "candidate"),
        (False, ["project:releng:snapcraft:firefox:beta"], "beta"),
        (False, ["project:releng:snapcraft:firefox:esr"], "esr/stable"),
        (False, ["project:releng:snapcraft:firefox:esr"], "esr/candidate"),
        (False, ["project:releng:snapcraft:firefox:mock"], "mock"),
        (False, ["project:releng:snapcraft:firefox:beta", "some:other:scope"], "beta"),
        (False, ["project:releng:snapcraft:firefox:beta", "project:releng:snapcraft:firefox:candidate"], "beta"),
        (True, ["project:releng:snapcraft:firefox:candidate"], "beta"),
        (True, ["project:releng:snapcraft:firefox:beta"], "esr/stable"),
    ),
)
def test_get_snap_channel_prod(raises, scopes, channel):
    task = {"scopes": scopes, "payload": {"channel": channel}}
    config = {"push_to_store": True}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_snap_channel(config, task)
    else:
        assert get_snap_channel(config, task) == channel


@pytest.mark.parametrize(
    "channel, push_to_store, expected",
    (
        ("beta", True, True),
        ("candidate", True, True),
        ("esr/stable", True, True),
        ("esr/candidate", True, True),
        ("beta", False, False),
        ("candidate", False, False),
        ("esr/stable", False, False),
        ("esr/candidate", False, False),
        ("mock", True, False),
        ("mock", False, False),
    ),
)
def test_is_allowed_to_push_to_snap_store(channel, push_to_store, expected):
    config = {"push_to_store": push_to_store}
    assert is_allowed_to_push_to_snap_store(config, channel) == expected
