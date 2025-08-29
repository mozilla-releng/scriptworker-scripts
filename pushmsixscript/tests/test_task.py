import pytest
from scriptworker_client.exceptions import TaskVerificationError

from pushmsixscript.task import get_msix_channel, is_allowed_to_push_to_microsoft_store


def test_get_msix_channel_without_payload_raises():
    task = {"payload": {}}
    config = {}
    with pytest.raises(TaskVerificationError):
        get_msix_channel(config, task)


@pytest.mark.parametrize("raises, channel", ((False, "release"), (False, "mock"), (True, "bogus")))
def test_get_msix_channel_dep(raises, channel):
    task = {"scopes": [], "payload": {"channel": channel}}
    config = {"push_to_store": False, "taskcluster_scope_prefix": "project:releng:microsoftstore:"}
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
        (True, ["project:releng:microsoftstore:release"], "bogus"),
    ),
)
def test_get_msix_channel_prod(raises, scopes, channel):
    task = {"scopes": scopes, "payload": {"channel": channel}}
    config = {"push_to_store": True, "taskcluster_scope_prefix": "project:releng:microsoftstore:"}
    if raises:
        with pytest.raises(TaskVerificationError):
            get_msix_channel(config, task)
    else:
        assert get_msix_channel(config, task) == channel


@pytest.mark.parametrize(
    "channel, push_to_store, expected",
    (
        ("beta", True, True),
        ("beta", False, False),
        ("release", True, True),
        ("release", False, False),
        ("mock", True, False),
        ("mock", False, False),
    ),
)
def test_is_allowed_to_push_to_microsoft_store(channel, push_to_store, expected):
    config = {"push_to_store": push_to_store, "taskcluster_scope_prefix": "project:releng:microsoftstore:"}
    assert is_allowed_to_push_to_microsoft_store(config, channel) == expected
