import shipitapi

from freezegun import freeze_time
from unittest.mock import MagicMock

from shipitscript.ship_actions import mark_as_shipped


@freeze_time('2018-01-19 12:59:59')
def test_mark_as_shipped(monkeypatch):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release', ReleaseClassMock)

    ship_it_instance_config = {
        'username': 'some-username',
        'password': 'some-password',
        'api_root': 'http://some.ship-it.tld/api/root',
        'timeout_in_seconds': 1,
    }
    release_name = 'Firefox-59.0b1-build1'
    mark_as_shipped(ship_it_instance_config, release_name)

    ReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=1,
    )
    release_instance_mock.update.assert_called_with(
        'Firefox-59.0b1-build1', status='shipped', shippedAt='2018-01-19 12:59:59'
    )
