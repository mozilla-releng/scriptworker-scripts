import pytest

from shipitscript.utils import get_auth_primitives


@pytest.mark.parametrize('ship_it_instance_config,expected', (
    ({
        'api_root': 'http://some-ship-it.url',
        'timeout_in_seconds': 1,
        'username': 'some-username',
        'password': 'some-password'
    }, (('some-username', 'some-password'), 'http://some-ship-it.url', 1)),
    ({
        'api_root': 'http://some-ship-it.url',
        'username': 'some-username',
        'password': 'some-password'
    }, (('some-username', 'some-password'), 'http://some-ship-it.url', 60)),
))
def test_get_auth_primitives(ship_it_instance_config, expected):
    assert get_auth_primitives(ship_it_instance_config) == expected
