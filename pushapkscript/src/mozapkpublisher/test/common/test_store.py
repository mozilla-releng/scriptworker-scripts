import argparse
import json

from mock import ANY, patch, Mock
import pytest
import random

from httplib2 import Response
from googleapiclient.errors import HttpError
from unittest.mock import MagicMock

from mozapkpublisher.common import store
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.store import add_general_google_play_arguments, \
    GooglePlayEdit, _create_google_edit_resource
from mozapkpublisher.test import does_not_raise


def test_add_general_google_play_arguments():
    parser = argparse.ArgumentParser()
    add_general_google_play_arguments(parser)

    config = parser.parse_args([
        '--credentials', 'credentials.json'
    ])
    assert config.google_play_credentials_filename == 'credentials.json'


def test_google_edit_resource_for_options_contact(monkeypatch):
    service_mock = MagicMock()
    service_mock.edits.return_value = 'edit resource'
    monkeypatch.setattr(store.service_account.Credentials, 'from_service_account_file',
                        lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(store, 'build', lambda *args, **kwargs: service_mock)
    edit_resource = _create_google_edit_resource(True, 'credentials_filename')
    assert edit_resource == 'edit resource'


def test_google_edit_resource_for_options_do_not_contact():
    edit_resource = _create_google_edit_resource(False, None)
    assert isinstance(edit_resource, MagicMock)


@pytest.fixture
def edit_resource_mock():
    edit_resource = MagicMock()
    new_transaction_mock = MagicMock()

    new_transaction_mock.execute = lambda: {'id': random.randint(0, 1000)}
    edit_resource.insert = lambda body, packageName: new_transaction_mock
    return edit_resource


def test_google_rollout_without_rollout_percentage():
    # Note: specifying "track='rollout'" (even with a valid percentage) is currently deprecated
    with GooglePlayEdit.transaction(None, 'dummy_package_name', contact_server=False,
                                    dry_run=True) as edit:
        with pytest.raises(WrongArgumentGiven):
            edit._update_track('rollout', [1], None)


@patch.object(store, '_create_google_edit_resource')
def test_google_valid_rollout_percentage_with_track_rollout(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, 'dummy_package_name', contact_server=False,
                                    dry_run=True) as edit:
        edit._update_track('rollout', [1], 50)

    raw_tracks_update = mock_edits_resource.tracks().method_calls[0][2]
    assert raw_tracks_update['track'] == 'production'
    assert raw_tracks_update['body'] == {
        'releases': [{
            'status': 'inProgress',
            'userFraction': 0.5,
            'versionCodes': [1]
        }],
        'track': 'production',
    }


@patch.object(store, '_create_google_edit_resource')
def test_google_valid_rollout_percentage_with_real_track(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, 'dummy_package_name', contact_server=False,
                                    dry_run=True) as edit:
        edit._update_track('beta', [1, 2], 20)

    raw_tracks_update = mock_edits_resource.tracks().method_calls[0][2]
    assert raw_tracks_update['track'] == 'beta'
    assert raw_tracks_update['body'] == {
        'releases': [{
            'status': 'inProgress',
            'userFraction': 0.2,
            'versionCodes': [1, 2]
        }],
        'track': 'beta',
    }


@patch.object(store, '_create_google_edit_resource')
def test_google_play_edit_commit_transaction(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, 'dummy_package_name', contact_server=False,
                                    dry_run=False) as _:
        pass

    mock_edits_resource.commit.assert_called_with(editId=ANY, packageName='dummy_package_name')


@patch.object(store, '_create_google_edit_resource')
def test_google_play_edit_no_commit_transaction(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, 'dummy_package_name', contact_server=False,
                                    dry_run=True) as _:
        pass

    mock_edits_resource.commit.assert_not_called()


def test_google_update_app():
    edit = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')
    edit.upload_apk = MagicMock()
    edit._update_track = MagicMock()
    apk_mock = Mock()
    apk_mock.name = '/path/to/dummy.apk'
    edit.update_app([(apk_mock, {'version_code': 1})], 'alpha')

    edit.upload_apk.assert_called_once_with(apk_mock)
    edit._update_track.assert_called_once_with('alpha', [1], None)


def test_google_get_track_status(edit_resource_mock):
    release_data = {
        "releases": [{
            "name": "61.0",
            "versionCodes": ["2015506297", "2015506300", "2015565729", "2015565732"],
            "releaseNotes": [
                {
                    "language": "sk",
                    "text": "* Vylepšenia v rámci Quantum CSS, ktoré urýchľujú načítanie stránok\n* Rýchlejšie posúvanie sa na stránkach",
                }
            ],
            "status": "inProgress",
            "userFraction": 0.1,
        }, {
            "name": "60.0.1",
            "versionCodes": ["2015558697", "2015558700"],
            "status": "completed",
        }],
    }

    edit_resource_mock.tracks().get().execute.return_value = release_data

    edit_resource_mock.tracks().get.reset_mock()

    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')
    assert google_play.get_track_status(track='production') == release_data
    edit_resource_mock.tracks().get.assert_called_once_with(
        editId=1,
        track='production',
        packageName='dummy_package_name',
    )


def test_google_upload_apk_returns_files_metadata(edit_resource_mock):
    edit_resource_mock.apks().upload().execute.return_value = {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }
    edit_resource_mock.apks().upload.reset_mock()

    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')
    apk_mock = Mock()
    apk_mock.name = '/path/to/dummy.apk'
    google_play.upload_apk(apk_mock)
    edit_resource_mock.apks().upload.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        media_body='/path/to/dummy.apk',
    )


@pytest.mark.parametrize('http_status_code', (400, 403))
def test_google_upload_apk_errors_out(edit_resource_mock, http_status_code):
    edit_resource_mock.apks().upload().execute.side_effect = HttpError(
        # XXX status is presented as a string by googleapiclient
        resp=Response({'status': str(http_status_code)}),
        # XXX content must be bytes
        # https://github.com/googleapis/google-api-python-client/blob/ffea1a7fe9d381d23ab59048263c631cc2b45323/googleapiclient/errors.py#L41
        content=b'{"error": {"errors": [{"reason": "someRandomReason"}] } }',
    )
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    with pytest.raises(HttpError):
        apk_mock = Mock()
        apk_mock.name = '/path/to/dummy.apk'
        google_play.upload_apk(apk_mock)


@pytest.mark.parametrize('reason, expectation', (
    ('apkUpgradeVersionConflict', does_not_raise()),
    ('apkNotificationMessageKeyUpgradeVersionConflict', does_not_raise()),
    ('someRandomReason', pytest.raises(HttpError)),
))
def test_google_upload_apk_does_not_error_out_when_apk_is_already_published(edit_resource_mock,
                                                                            reason, expectation):
    content = {
        'error': {
            'errors': [{
                'reason': reason
            }],
        },
    }
    # XXX content must be bytes
    # https://github.com/googleapis/google-api-python-client/blob/ffea1a7fe9d381d23ab59048263c631cc2b45323/googleapiclient/errors.py#L41
    content_bytes = json.dumps(content).encode('ascii')

    edit_resource_mock.apks().upload().execute.side_effect = HttpError(
        # XXX status is presented as a string by googleapiclient
        resp=Response({'status': '403'}),
        content=content_bytes,
    )
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    with expectation:
        apk_mock = Mock()
        apk_mock.name = '/path/to/dummy.apk'
        google_play.upload_apk(apk_mock)


def test_google_update_track(edit_resource_mock):
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    google_play._update_track('alpha', ['2015012345', '2015012347'])
    edit_resource_mock.tracks().update.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        track='alpha',
        body={
            'releases': [{
                'status': 'completed',
                'versionCodes': ['2015012345', '2015012347'],
            }],
            'track': 'alpha',
        },
    )

    edit_resource_mock.tracks().update.reset_mock()
    google_play._update_track('production', ['2015012345', '2015012347'], rollout_percentage=1)
    edit_resource_mock.tracks().update.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        track='production',
        body={
            'releases': [{
                'status': 'inProgress',
                'userFraction': 0.01,
                'versionCodes': ['2015012345', '2015012347']},
            ],
            'track': 'production',
        },
    )


@pytest.mark.parametrize('invalid_percentage', (-1, 101))
def test_google_update_track_should_refuse_wrong_percentage(edit_resource_mock,
                                                            invalid_percentage):
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    with pytest.raises(WrongArgumentGiven):
        google_play._update_track('production', ['2015012345', '2015012347'], invalid_percentage)


def test_google_update_listings(edit_resource_mock):
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    google_play.update_listings(
        'en-GB',
        title='Firefox for Android Beta',
        full_description='Long description',
        short_description='Short',
    )
    edit_resource_mock.listings().update.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        language='en-GB',
        body={
            'title': 'Firefox for Android Beta',
            'fullDescription': 'Long description',
            'shortDescription': 'Short',
        }
    )


def test_google_update_whats_new(edit_resource_mock):
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    google_play.update_whats_new('en-GB', '2015012345', 'Check out this cool feature!')
    edit_resource_mock.apklistings().update.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        language='en-GB',
        apkVersionCode='2015012345',
        body={'recentChanges': 'Check out this cool feature!'}
    )


def test_google_update_aab():
    edit = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')
    edit.upload_aab = MagicMock()
    edit._update_track = MagicMock()
    aab_mock = Mock()
    aab_mock.name = '/path/to/dummy.aab'
    edit.update_aab([(aab_mock, {'version_code': 1})], 'alpha')

    edit.upload_aab.assert_called_once_with(aab_mock)
    edit._update_track.assert_called_once_with('alpha', [1], None)


def test_google_upload_aab_returns_files_metadata(edit_resource_mock):
    edit_resource_mock.bundles().upload().execute.return_value = {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }
    edit_resource_mock.bundles().upload.reset_mock()

    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')
    aab_mock = Mock()
    aab_mock.name = '/path/to/dummy.aab'
    google_play.upload_aab(aab_mock)
    edit_resource_mock.bundles().upload.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        media_body='/path/to/dummy.aab',
        media_mime_type='application/octet-stream',
    )


@pytest.mark.parametrize('http_status_code', (400, 403))
def test_google_upload_aab_errors_out(edit_resource_mock, http_status_code):
    edit_resource_mock.bundles().upload().execute.side_effect = HttpError(
        # XXX status is presented as a string by googleapiclient
        resp=Response({'status': str(http_status_code)}),
        # XXX content must be bytes
        # https://github.com/googleapis/google-api-python-client/blob/ffea1a7fe9d381d23ab59048263c631cc2b45323/googleapiclient/errors.py#L41
        content=b'{"error": {"errors": [{"reason": "someRandomReason"}] } }',
    )
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    with pytest.raises(HttpError):
        aab_mock = Mock()
        aab_mock.name = '/path/to/dummy.aab'
        google_play.upload_aab(aab_mock)


@pytest.mark.parametrize('reason, expectation', (
    ('someRandomReason', pytest.raises(HttpError)),
))
def test_google_upload_aab_does_not_error_out_when_aab_is_already_published(edit_resource_mock,
                                                                            reason, expectation):
    content = {
        'error': {
            'errors': [{
                'reason': reason
            }],
        },
    }
    # XXX content must be bytes
    # https://github.com/googleapis/google-api-python-client/blob/ffea1a7fe9d381d23ab59048263c631cc2b45323/googleapiclient/errors.py#L41
    content_bytes = json.dumps(content).encode('ascii')

    edit_resource_mock.bundles().upload().execute.side_effect = HttpError(
        # XXX status is presented as a string by googleapiclient
        resp=Response({'status': '403'}),
        content=content_bytes,
    )
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    with expectation:
        aab_mock = Mock()
        aab_mock.name = '/path/to/dummy.aab'
        google_play.upload_aab(aab_mock)
