import pytest
from unittest.mock import MagicMock

from freezegun import freeze_time
import shipitapi
from shipitscript.ship_actions import mark_as_shipped, mark_as_shipped_v2, mark_as_started


@freeze_time('2018-01-19 12:59:59')
@pytest.mark.parametrize('timeout, expected_timeout', (
    (1, 1),
    ('10', 10),
    (None, 60),
))
def test_mark_as_shipped(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    release_info = {
        'status': 'shipped',
        'shippedAt': '2018-01-19 12:59:59'
    }
    attrs = {
        'getRelease.return_value': release_info
    }
    release_instance_mock.configure_mock(**attrs)
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
def test_mark_as_shipped_v2(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    release_info = {
        'status': 'shipped',
    }
    attrs = {
        'getRelease.return_value': release_info
    }
    release_instance_mock.configure_mock(**attrs)
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release_V2', ReleaseClassMock)

    ship_it_instance_config = {
        'taskcluster_client_id': 'some-id',
        'taskcluster_access_token': 'some-token',
        'api_root_v2': 'http://some.ship-it.tld/api/root',
    }
    if timeout is not None:
        ship_it_instance_config['timeout_in_seconds'] = timeout
    release_name = 'Firefox-59.0b1-build1'

    mark_as_shipped_v2(ship_it_instance_config, release_name)

    ReleaseClassMock.assert_called_with(
        taskcluster_client_id='some-id',
        taskcluster_access_token='some-token',
        api_root='http://some.ship-it.tld/api/root',
        timeout=expected_timeout,
    )
    release_instance_mock.update_status.assert_called_with(
        'Firefox-59.0b1-build1', status='shipped'
    )


@pytest.mark.parametrize('timeout, expected_timeout', (
    (1, 1),
    ('10', 10),
    (None, 60),
))
def test_mark_as_started(monkeypatch, timeout, expected_timeout):
    ReleaseClassMock = MagicMock()
    NewReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    release_info = {
        'status': 'Started',
        'ready': True,
        'complete': True,
    }
    attrs = {
        'getRelease.return_value': release_info
    }
    release_instance_mock.configure_mock(**attrs)
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
        'Firefox-59.0b1-build1', ready=True, complete=True, status="Started"
    )
    NewReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=expected_timeout,
        csrf_token_prefix='firefox-'
    )
    new_release_instance_mock.submit.assert_called_with(**data)
