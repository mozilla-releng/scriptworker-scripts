import pytest
from unittest.mock import MagicMock

from scriptworker.exceptions import ScriptWorkerTaskException
from shipitscript.utils import (
    get_auth_primitives, check_release_has_values, same_timing
)


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


@pytest.mark.parametrize('release_info,  values, raises', (
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:00+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': True,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': True,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': 'shipped',
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'status': 'shipped',
        'shippedAt': '2018-07-03 09:19:00',
    }, False),
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:00+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': True,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': True,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': 'Started',
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'status': 'shipped',
        'shippedAt': '2018-07-03 09:19:00',
    }, True),
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:01+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': True,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': True,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': 'shipped',
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'status': 'shipped',
        'shippedAt': '2018-07-03 09:19:00',
    }, True),
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:01+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': True,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': True,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': 'shipped',
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'status': 'shipped',
        'shippedAt': '2018-07-02 08:03:00',
    }, True),
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:01+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': True,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': True,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': 'Started',
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'ready': True,
        'complete': True,
        'status': 'Started',
    }, False),
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:01+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': None,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': True,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': 'Started',
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'ready': True,
        'complete': True,
        'status': 'Started',
    }, True),
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:01+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': True,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': False,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': 'Started',
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'ready': True,
        'complete': True,
        'status': 'Started',
    }, True),
    ({
        'name': 'Fennec-X.0bX-build42',
        'shippedAt': '2018-07-03T09:19:01+00:00',
        'mh_changeset': '',
        'mozillaRelbranch': None,
        'version': 'X.0bX',
        'branch': 'projects/maple',
        'submitter': 'shipit-scriptworker-stage',
        'ready': True,
        'mozillaRevision': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'release_eta': None,
        'starter': None,
        'complete': False,
        'submittedAt': '2018-07-02T09:18:39+00:00',
        'status': None,
        'comment': None,
        'product': 'fennec',
        'description': None,
        'buildNumber': 42,
        'l10nChangesets': {},
    }, {
        'ready': True,
        'complete': True,
        'status': 'Started',
    }, True),
))
def test_generic_validation(monkeypatch, release_info,  values, raises):
    release_name = "Fennec-X.0bX-build42"
    ReleaseClassMock = MagicMock()
    attrs = {
        'getRelease.return_value': release_info
    }
    ReleaseClassMock.configure_mock(**attrs)

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_release_has_values(ReleaseClassMock, release_name, **values)
    else:
        check_release_has_values(ReleaseClassMock, release_name, **values)


@pytest.mark.parametrize('time1,time2, expected', (
    ('2018-07-02 16:51:04', '2018-07-02T16:51:04+00:00', True),
    ('2018-07-02 16:51:04', '2018-07-02T16:51:04+01:00', False),
    ('2018-07-02 16:51:04', '2018-07-02T16:51:04+00:11', False),
    ('2018-07-02 16:51:04', '2018-07-02T16:51:04', True),
))
def test_same_timing(time1, time2, expected):
    assert same_timing(time1, time2) == expected
