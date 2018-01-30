import pytest
import shipitapi

from freezegun import freeze_time
from unittest.mock import MagicMock

from shipitscript.ship_actions import mark_as_shipped


@freeze_time('2018-01-19 12:59:59')
@pytest.mark.parametrize('timeout, expected_timeout', (
    (1, 1),
    ('10', 10),
    (None, 60),
))
def test_mark_as_shipped(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release', ReleaseClassMock)

    ship_it_instance_config = {
        'username': 'some-username',
        'password': 'some-password',
        'api_root': 'http://some.ship-it.tld/api/root',
    }
    if timeout is not None:
        ship_it_instance_config['timeout_in_seconds'] = timeout
    release_name = 'Firefox-59.0b1-build1'
    mark_as_shipped(ship_it_instance_config, release_name)

    ReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=expected_timeout,
    )
    release_instance_mock.update.assert_called_with(
        'Firefox-59.0b1-build1', status='shipped', shippedAt='2018-01-19 12:59:59'
    )
