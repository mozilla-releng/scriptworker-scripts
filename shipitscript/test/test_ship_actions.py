import pytest
import shipitapi

from freezegun import freeze_time
from unittest.mock import MagicMock

from shipitscript.ship_actions import mark_as_shipped, mark_as_started


@freeze_time('2018-01-19 12:59:59')
@pytest.mark.parametrize('timeout, expected_timeout', (
    (1, 1),
    ('10', 10),
    (None, 60),
))
def test__mark_as_shipped(monkeypatch, timeout, expected_timeout):
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


@pytest.mark.parametrize('timeout, expected_timeout', (
    (1, 1),
    ('10', 10),
    (None, 60),
))
def test__mark_as_started(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    NewReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    new_release_instance_mock = MagicMock()
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    NewReleaseClassMock.side_effect = lambda *args, **kwargs: new_release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release', ReleaseClassMock)
    monkeypatch.setattr(shipitapi, 'NewRelease', NewReleaseClassMock)

    ship_it_instance_config = {
        'username': 'some-username',
        'password': 'some-password',
        'api_root': 'http://some.ship-it.tld/api/root',
    }
    if timeout is not None:
        ship_it_instance_config['timeout_in_seconds'] = timeout

    release_name = 'Firefox-59.0b1-build1'
    data = dict(
        product='firefox',
        version='99.0b1',
        buildNumber=1,
        branch='projects/maple',
        mozillaRevision='default',
        l10nChangesets='ro default',
        partials='98.0b1,98.0b14,98.0b15',
    )
    mark_as_started(ship_it_instance_config, release_name, data)

    ReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=expected_timeout,
    )
    release_instance_mock.update.assert_called_with(
        'Firefox-59.0b1-build1', ready=1, complete=1, status="Started"
    )
    NewReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=expected_timeout,
        csrf_token_prefix='firefox-'
    )
    new_release_instance_mock.submit.assert_called_with(**data)
