import pytest
from scriptworker.exceptions import TaskVerificationError

from pushmsixscript.task import get_msix_channel, is_allowed_to_push_to_microsoft_store


def test_get_msix_channel_without_payload_raises():
    task = {"payload": {}}
    config = {}
    with pytest.raises(TaskVerificationError):
        get_msix_channel(config, task)


"""
@pytest.mark.parametrize(
    "raises, channel", ((False, "release"), (False, "mock"), (True, "bogus"))
)
def test_get_msix_channel_dep(raises, channel):
    task = {"scopes": [], "payload": {"channel": channel}}
    config = {"push_to_store": False}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_msix_channel(config, task)
    else:
        assert get_msix_channel(config, task) == channel


@pytest.mark.parametrize(
    "raises, scopes, channel",
    (
        (False, ["project:releng:microsoftstore:release"], "release"),
        (False, ["project:releng:microsoftstore:mock"], "mock"),
        (True, ["project:releng:microsoftstore:release"], "beta"),
    ),
)
def test_get_msix_channel_prod(raises, scopes, channel):
    task = {"scopes": scopes, "payload": {"channel": channel}}
    config = {"push_to_store": True}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_msix_channel(config, task)
    else:
        assert get_msix_channel(config, task) == channel
"""


@pytest.mark.parametrize(
    "channel, push_to_store, expected",
    (
        ("release", True, True),
        ("release", False, False),
        ("mock", True, False),
        ("mock", False, False),
    ),
)
def test_is_allowed_to_push_to_microsoft_store(channel, push_to_store, expected):
    config = {"push_to_store": push_to_store}
    assert is_allowed_to_push_to_microsoft_store(config, channel) == expected
