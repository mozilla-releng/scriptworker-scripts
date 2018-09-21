import contextlib
import pytest
import tempfile

from mozilla_version.gecko import GeckoSnapVersion
from scriptworker.exceptions import TaskVerificationError
from unittest.mock import MagicMock

from pushsnapscript.exceptions import AlreadyLatestError
from pushsnapscript import snap_store


@pytest.mark.parametrize('channel, expected_macaroon_location, raises, exception_message, bubbles_up_exception', ((
    'beta',
    '/path/to/macaroon_beta',
    False,
    None,
    False,
), (
    'candidate',
    '/path/to/macaroon_candidate',
    False,
    None,
    False,
), (
    'candidate',
    '/path/to/macaroon_candidate',
    True,
    'some random message',
    True
), (
    'candidate',
    '/path/to/macaroon_candidate',
    True,
    'A file with this exact same content has already been uploaded',
    False,
)))
def test_push(monkeypatch, channel, expected_macaroon_location, raises, exception_message, bubbles_up_exception):
    fake_release_if_needed_count = (n for n in range(0, 2))

    context = MagicMock()
    context.config = {
        'macaroons_locations': {
            'beta': '/path/to/macaroon_beta',
            'candidate': '/path/to/macaroon_candidate',
        }
    }
    store = MagicMock()
    store_client_mock = MagicMock()

    @contextlib.contextmanager
    def fake_store_session(macaroon_location):
        assert macaroon_location == expected_macaroon_location
        yield store

    monkeypatch.setattr(snap_store, '_store_session', fake_store_session)
    monkeypatch.setattr(snap_store, 'snapcraft_store_client', store_client_mock)
    store_client_mock.push.side_effect = snap_store.StoreReviewError({
            'errors': [{'message': exception_message}],
            'code': 'processing_error',
        }) if raises else None

    def fake_release_if_needed(store_, channel_, snap_file_path):
        assert store_ is store
        assert channel_ == channel_
        assert snap_file_path == '/path/to/snap'
        next(fake_release_if_needed_count)

    monkeypatch.setattr(snap_store, '_release_if_needed', fake_release_if_needed)

    if bubbles_up_exception:
        with pytest.raises(snap_store.StoreReviewError):
            snap_store.push(context, '/path/to/snap', channel)
        assert next(fake_release_if_needed_count) == 0
    else:
        snap_store.push(context, '/path/to/snap', channel)
        assert next(fake_release_if_needed_count) == 1


def test_push_early_return_if_not_allowed(monkeypatch):
    call_count = (n for n in range(0, 2))

    context = MagicMock()

    def increase_call_count(_, __):
        next(call_count)

    monkeypatch.setattr(snap_store.snapcraft_store_client, 'push', increase_call_count)
    snap_store.push(context, '/some/file.snap', channel='mock')

    assert next(call_count) == 0


class SomeSpecificException(Exception):
    pass


@pytest.mark.parametrize('raises', (True, False))
def test_store_session(monkeypatch, raises):
    store_client_mock = MagicMock()
    monkeypatch.setattr(snap_store, 'StoreClient', lambda: store_client_mock)

    with tempfile.NamedTemporaryFile('w+') as fake_macaroon:
        if raises:
            with pytest.raises(SomeSpecificException):
                with snap_store._store_session(fake_macaroon.name):
                    store_client_mock.login.assert_called_once()
                    store_client_mock.logout.assert_not_called()
                    raise SomeSpecificException('Oh noes!')
        else:
            with snap_store._store_session(fake_macaroon.name):
                store_client_mock.login.assert_called_once()
                store_client_mock.logout.assert_not_called()

        assert store_client_mock.login.call_count == 1
        store_client_mock.logout.assert_called_once_with()


@pytest.mark.parametrize('channel, raises, exception, bubbles_up_exception, must_release, release_kwargs', ((
    'beta', True, TaskVerificationError, True, False, None
), (
    'beta', True, AlreadyLatestError, False, False, None
), (
    'beta', False, None, False, True, {
        'snap_name': 'firefox',
        'revision': 3,
        'channels': ['beta']
    }
), (
    'stable', False, None, False, True, {
        'snap_name': 'firefox',
        'revision': 3,
        'channels': ['stable']
    }
)))
def test_release_if_needed(monkeypatch, channel, raises, exception, bubbles_up_exception, must_release, release_kwargs):
    store = MagicMock()

    def return_dummy(*args, **kwargs):
        return 'dummy'

    def return_dummy_tuple(*args, **kwargs):
        return ('dummy', 'tuple')

    monkeypatch.setattr(snap_store, '_list_all_revisions', return_dummy)
    monkeypatch.setattr(snap_store, '_pluck_metadata', return_dummy)
    monkeypatch.setattr(snap_store, '_filter_versions_that_are_not_the_same_type', return_dummy)
    monkeypatch.setattr(snap_store, '_populate_sha3_384', return_dummy)
    monkeypatch.setattr(snap_store, 'get_hash', return_dummy)
    monkeypatch.setattr(snap_store, '_find_revision_and_version_of_current_snap', lambda _, __: (3, 'version'))
    monkeypatch.setattr(snap_store, '_pick_revision_and_version_of_latest_released_snap', return_dummy_tuple)

    def check_current(*args):
        if raises:
            if exception == AlreadyLatestError:
                raise exception('version', 'rev')
            else:
                raise exception('some message')

    monkeypatch.setattr(snap_store, '_check_current_snap_is_not_released', check_current)

    if bubbles_up_exception:
        with pytest.raises(exception):
            snap_store._release_if_needed(store, channel, '/path/to/snap')
    else:
        snap_store._release_if_needed(store, channel, '/path/to/snap')

    if must_release:
        store.release.assert_called_once_with(**release_kwargs)
    else:
        store.release.assert_not_called()


def test_list_all_revisions():
    store = MagicMock()
    store.get_snap_revisions.return_value = [{
        'revision': 1,
        'version': '63.0b1-1',
        'current_channels': [],
        'some_other': 'field',
    }, {
        'revision': 2,
        'version': '63.0b2-1',
        'current_channels': [],
    }]

    assert snap_store._list_all_revisions(store) == [{
        'revision': 1,
        'version': '63.0b1-1',
        'current_channels': [],
        'some_other': 'field',
    }, {
        'revision': 2,
        'version': '63.0b2-1',
        'current_channels': [],
    }]
    store.get_snap_revisions.assert_called_once_with('firefox')


def test_pluck_metadata():
    assert snap_store._pluck_metadata([{
        'revision': 1,
        'version': '63.0b1-1',
        'current_channels': [],
        'some_other': 'field',
    }, {
        'revision': 2,
        'version': '63.0b2-1',
        'current_channels': [],
    }, {
        'revision': 3,
        'version': '62.0-1',
        'current_channels': ['release', 'candidate'],
    }, {
        'revision': 4,
        'version': '63.0b3-1',
        'current_channels': ['beta', 'edge'],
    }, {
        'revision': 5,
        'version': '60.2.1esr-1',
        'current_channels': ['esr/stable', 'esr/candidate', 'esr/beta', 'esr/edge'],
    }]) == {
        1: {
            'version': GeckoSnapVersion.parse('63.0b1-1'),
            'current_channels': [],
        },
        2: {
            'version': GeckoSnapVersion.parse('63.0b2-1'),
            'current_channels': [],
        },
        3: {
            'version': GeckoSnapVersion.parse('62.0-1'),
            'current_channels': ['release', 'candidate'],
        },
        4: {
            'version': GeckoSnapVersion.parse('63.0b3-1'),
            'current_channels': ['beta', 'edge'],
        },
        5: {
            'version': GeckoSnapVersion.parse('60.2.1esr-1'),
            'current_channels': ['esr/stable', 'esr/candidate', 'esr/beta', 'esr/edge'],
        },
    }


@pytest.mark.parametrize('channel, expected', ((
    'beta', {
        1: {
            'version': GeckoSnapVersion.parse('63.0b1-1'),
        },
        2: {
            'version': GeckoSnapVersion.parse('63.0b2-1'),
        },
        4: {
            'version': GeckoSnapVersion.parse('63.0b3-1'),
        },
    }
), (
    'stable', {
        3: {
            'version': GeckoSnapVersion.parse('62.0-1'),
        },
    }
), (
    'esr', {
        5: {
            'version': GeckoSnapVersion.parse('60.2.1esr-1'),
        },
    }
), (
    'esr/stable', {
        5: {
            'version': GeckoSnapVersion.parse('60.2.1esr-1'),
        },
    }
), (
    'esr/candidate', {
        5: {
            'version': GeckoSnapVersion.parse('60.2.1esr-1'),
        },
    }
)))
def test_filter_versions_that_are_not_the_same_type(channel, expected):
    assert snap_store._filter_versions_that_are_not_the_same_type({
        1: {
            'version': GeckoSnapVersion.parse('63.0b1-1'),
        },
        2: {
            'version': GeckoSnapVersion.parse('63.0b2-1'),
        },
        3: {
            'version': GeckoSnapVersion.parse('62.0-1'),
        },
        4: {
            'version': GeckoSnapVersion.parse('63.0b3-1'),
        },
        5: {
            'version': GeckoSnapVersion.parse('60.2.1esr-1'),
        },
    }, channel) == expected


def test_populate_sha3_384(monkeypatch):
    metadata_per_revision = {
        1: {
            'version': '63.0b1-1',
            'current_channels': []
        },
        2: {
            'version': '63.0b2-1',
            'current_channels': ['beta']
        },
        3: {
            'version': '63.0b3-1',
            'current_channels': ['beta']
        },
    }

    def gen_fake_hash(_, revision):
        return 'fake_hash_rev{}'.format(revision)

    store = MagicMock()

    monkeypatch.setattr(snap_store, '_get_from_sha3_384_from_revision', gen_fake_hash)

    assert snap_store._populate_sha3_384(store, metadata_per_revision) == {
        2: {
            'version': '63.0b2-1',
            'current_channels': ['beta'],
            'download_sha3_384': 'fake_hash_rev2',
        },
        3: {
            'version': '63.0b3-1',
            'current_channels': ['beta'],
            'download_sha3_384': 'fake_hash_rev3',
        },
    }


def test_get_from_sha3_384_from_revision():
    store = MagicMock()
    store.cpi.get_default_headers.return_value = {'some_default': 'header'}
    store_get_mock = MagicMock()
    store_get_mock.json.return_value = {'download_sha3_384': 'some_sha3_384'}
    store.cpi.get.return_value = store_get_mock

    assert snap_store._get_from_sha3_384_from_revision(store, 2) == 'some_sha3_384'
    store.cpi.get.assert_called_once_with(
        'api/v1/snaps/details/firefox',
        headers={
            'some_default': 'header',
            'Accept': 'application/hal+json',
            'X-Ubuntu-Series': '16',
        },
        params={
            'fields': 'status,download_sha3_384,revision',
            'revision': 2
        }
    )


@pytest.mark.parametrize('metadata_per_revision, raises, expected', ((
    {
        2: {
            'version': '63.0b6-1',
            'download_sha3_384': 'a_hash'
        },
        3: {
            'version': '63.0b6-2',
            'download_sha3_384': 'some_sha3_384',
        },
        4: {
            'version': '63.0b7-1',
            'download_sha3_384': 'another_hash',
        },
    },
    False,
    (3, '63.0b6-2')
), (
    {
        2: {
            'version': '63.0b6-1',
            'download_sha3_384': 'a_hash'
        },
    },
    True,
    ValueError,
), (
    {
        3: {
            'version': '63.0b6-2',
            'download_sha3_384': 'some_sha3_384',
        },
        4: {
            'version': '63.0b7-1',
            'download_sha3_384': 'some_sha3_384',
        },
    },
    True,
    ValueError,
)))
def test_find_revision_and_version_of_current_snap(metadata_per_revision, raises, expected):
    if raises:
        with pytest.raises(expected):
            snap_store._find_revision_and_version_of_current_snap(metadata_per_revision, 'some_sha3_384')
    else:
        snap_store._find_revision_and_version_of_current_snap(metadata_per_revision, 'some_sha3_384')


@pytest.mark.parametrize('current_revision, current_version, latest_released_revision, latest_released_version, raises, expected', ((
    131, GeckoSnapVersion.parse('63.0b8-1'), 130, GeckoSnapVersion.parse('63.0b7-1'), False, None,
), (
    131, GeckoSnapVersion.parse('63.0b8-1'), 131, GeckoSnapVersion.parse('63.0b8-1'), True, AlreadyLatestError,
), (
    133, GeckoSnapVersion.parse('62.0.2-1'), 131, GeckoSnapVersion.parse('63.0b8-1'), True, TaskVerificationError,
), (
    130, GeckoSnapVersion.parse('63.0b7-1'), 131, GeckoSnapVersion.parse('63.0b8-1'), True, TaskVerificationError,
), (
    132, GeckoSnapVersion.parse('63.0b8-1'), 131, GeckoSnapVersion.parse('63.0b8-1'), True, TaskVerificationError,
), (
    130, GeckoSnapVersion.parse('63.0b8-1'), 131, GeckoSnapVersion.parse('63.0b8-1'), True, TaskVerificationError,
)))
def test_check_current_snap_is_not_released(current_revision, current_version, latest_released_version, latest_released_revision, raises, expected):
    if raises:
        with pytest.raises(expected):
            snap_store._check_current_snap_is_not_released(current_revision, current_version, latest_released_revision, latest_released_version)
    else:
        snap_store._check_current_snap_is_not_released(current_revision, current_version, latest_released_revision, latest_released_version)


@pytest.mark.parametrize('channel, metadata_per_revision, raises, expected', ((
    'beta',
    {
        2: {
            'version': '63.0b6-1',
            'current_channels': [],
        },
        3: {
            'version': '63.0b6-2',
            'current_channels': [],
        },
        4: {
            'version': '63.0b7-1',
            'current_channels': ['beta', 'edge'],
        },
    },
    False,
    (4, '63.0b7-1'),
), (
    'beta',
    {
        2: {
            'version': '63.0b6-1',
            'current_channels': [],
        },
        3: {
            'version': '63.0b6-2',
            'current_channels': [],
        },
        4: {
            'version': '63.0b7-1',
            'current_channels': ['beta', 'edge'],
        },
        5: {
            'version': '63.0b7-2',
            'current_channels': [],
        },
    },
    False,
    (4, '63.0b7-1'),
), (
    'beta',
    {
        2: {
            'version': '63.0b6-1',
            'current_channels': [],
        },
        3: {
            'version': '63.0b6-2',
            'current_channels': [],
        },
        4: {
            'version': '63.0b7-1',
            'current_channels': [],
        },
    },
    True,
    ValueError,
), (
    'beta',
    {
        2: {
            'version': '63.0b6-1',
            'current_channels': [],
        },
        3: {
            'version': '63.0b6-2',
            'current_channels': ['beta'],
        },
        4: {
            'version': '63.0b7-1',
            'current_channels': ['beta', 'edge'],
        },
    },
    True,
    ValueError,
)))
def test_pick_revision_and_version_of_latest_released_snap(channel, metadata_per_revision, raises, expected):
    if raises:
        with pytest.raises(expected):
            snap_store._pick_revision_and_version_of_latest_released_snap(channel, metadata_per_revision)
    else:
        assert snap_store._pick_revision_and_version_of_latest_released_snap(channel, metadata_per_revision) == expected
