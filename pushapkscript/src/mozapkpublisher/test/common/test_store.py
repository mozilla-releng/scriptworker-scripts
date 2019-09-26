import argparse
import json

from mock import ANY, patch, Mock, call
import pytest
import random

from googleapiclient.errors import HttpError
from unittest.mock import MagicMock

from mozapkpublisher.common import store
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.store import add_general_google_play_arguments, \
    GooglePlayEdit, _create_google_edit_resource, AmazonStoreEdit, AmazonAuth, MockAmazonStoreEdit
from mozapkpublisher.test import does_not_raise


def test_add_general_google_play_arguments():
    parser = argparse.ArgumentParser()
    add_general_google_play_arguments(parser)

    config = parser.parse_args([
        '--service-account', 'dummy@dummy', '--credentials', 'credentials.p12'
    ])
    assert config.google_play_credentials_filename == 'credentials.p12'
    assert config.service_account == 'dummy@dummy'


@patch.object(store.requests, 'request', return_value=Mock(status_code=500, text="oops"))
def test_http_raise_if_mismatched_status(_):
    with pytest.raises(RuntimeError):
        store.http(200, 'get', 'http://fake')


@patch.object(store.requests, 'request', return_value=Mock(status_code=200, text='body'))
def test_http_return_response(_):
    assert store.http(200, 'get', 'http://fake').text == 'body'


def test_amazon_auth():
    auth = AmazonAuth('token')
    request = Mock(headers={})
    auth(request)
    assert request.headers['Authorization'] == 'Bearer token'


@patch.object(store, 'http', return_value=Mock(status_code=200))
def test_edit_http(mock_http):
    edit = AmazonStoreEdit('auth', 'edit_id', 'dummy_package_name')
    edit._http(200, 'get', '/endpoint')
    mock_http.assert_called_once_with(200, 'get', 'https://developer.amazon.com/api/appstore/v1/'
                                                  'applications/dummy_package_name/edits/edit_id/'
                                                  'endpoint', auth='auth')


@patch.object(store, 'http')
def test_amazon_do_not_contact_server(http_mock):
    with AmazonStoreEdit.transaction('client id', 'client secret', 'package.name',
                                     contact_server=False, dry_run=False) as edit:
        edit.update_app(('apk', None))

    with AmazonStoreEdit.transaction('client id', 'client secret', 'package.name',
                                     contact_server=False, dry_run=True) as edit:
        edit.update_app(('apk', None))

    http_mock.assert_not_called()


def test_amazon_update_app():
    edit = AmazonStoreEdit(None, None, 'dummy_package_name')
    with patch.object(edit, '_http') as mock_http:
        mock_http.side_effect = [
            Mock(json=lambda: [{'id': 'apk_id'}]),
            Mock(headers={'ETag': 'apk etag'}),
            None,
            None,
            Mock(json=lambda: {'listings': {'en-US': {}}}),
            Mock(headers={'ETag': 'listing etag'}, json=lambda: {}),
            None,
        ]

        edit.update_app([('apk', None)])
        mock_http.assert_any_call(200, 'post', '/apks/upload', data='apk',
                                  headers={'Content-Type': 'application/octet-stream'})


def test_amazon_release_notes():
    edit = AmazonStoreEdit(None, None, 'dummy_package_name')
    with patch.object(edit, '_http') as mock_http:
        mock_http.side_effect = [
            Mock(json=lambda: [{'id': 'apk_id'}]),
            Mock(headers={'ETag': 'apk etag'}),
            None,
            None,
            Mock(json=lambda: {'listings': {'sv-SE': {}, 'fr-FR': {}}}),
            Mock(headers={'ETag': 'listing etag'}, json=lambda: {}),
            None,
            Mock(headers={'ETag': 'listing etag'}, json=lambda: {}),
            None,
        ]
        edit.update_app([('apk', None)])

        mock_http.assert_any_call(
            200,
            'put',
            '/listings/fr-FR',
            headers={'If-Match': 'listing etag'},
            json={'recentChanges': 'Correction de bugs et amélioration des techniques.'}
        )
        mock_http.assert_any_call(200, 'put', '/listings/sv-SE',
                                  headers={'If-Match': 'listing etag'},
                                  json={'recentChanges': '✔'})


def test_amazon_transaction_contact_and_keep():
    with patch.object(store, 'http') as mock_http:
        mock_http.side_effect = [
            Mock(status_code=200, json=lambda: {'access_token': 'token'}),
            Mock(status_code=200, text='{}'),
            Mock(status_code=200, json=lambda: {'id': 'edit_id'}),
            Mock(status_code=200, headers={'ETag': 'edit_etag'}),
            Mock(status_code=200),
        ]
        with AmazonStoreEdit.transaction('client id', 'client secret', 'dummy_package_name',
                                         contact_server=True, dry_run=False):
            pass

        mock_http.assert_any_call(200, 'post', 'https://api.amazon.com/auth/o2/token', data={
            'client_id': 'client id',
            'client_secret': 'client secret',
            'grant_type': ANY,
            'scope': ANY
        })

        assert call(200, 'post', 'https://developer.amazon.com/api/appstore/v1/applications/'
                                 'dummy_package_name/edits/edit_id/commit',
                    headers={'If-Match': 'edit_etag'},
                    auth=ANY) not in mock_http.call_args_list


def test_amazon_transaction_contact_dry_run():
    with patch.object(store, 'http') as mock_http:
        mock_http.side_effect = [
            Mock(status_code=200, json=lambda: {'access_token': 'token'}),
            Mock(status_code=200, text='{}'),
            Mock(status_code=200, json=lambda: {'id': 'edit_id'}),
            Mock(status_code=200),
            Mock(status_code=200, headers={'ETag': 'edit_etag'}),
            Mock(status_code=204),
        ]
        with AmazonStoreEdit.transaction('client id', 'client secret', 'dummy_package_name',
                                         contact_server=True, dry_run=True):
            pass

        mock_http.assert_any_call(200, 'post', 'https://developer.amazon.com/api/appstore/v1/'
                                               'applications/dummy_package_name/edits/edit_id/'
                                               'validate',
                                  auth=ANY)
        mock_http.assert_any_call(204, 'delete', 'https://developer.amazon.com/api/appstore/v1/'
                                                 'applications/dummy_package_name/edits/edit_id',
                                  headers={'If-Match': 'edit_etag'},
                                  auth=ANY)


def test_amazon_transaction_existing_upcoming_version():
    with patch.object(store, 'http') as mock_http:
        mock_http.side_effect = [
            Mock(status_code=200, json=lambda: {'access_token': 'token'}),
            Mock(status_code=200, text='{"id": "...", "status": "IN_PROGRESS"}'),
        ]

    with pytest.raises(RuntimeError):
        with AmazonStoreEdit.transaction('client id', 'client secret', 'dummy_package_name',
                                         contact_server=True, dry_run=False):
            pass


def test_amazon_transaction_cancel_on_exception():
    with patch.object(store, 'http') as mock_http:
        mock_http.side_effect = [
            Mock(status_code=200, json=lambda: {'access_token': 'token'}),
            Mock(status_code=200, text='{}'),
            Mock(status_code=200, json=lambda: {'id': 'edit_id'}),
            Mock(status_code=200, headers={'ETag': 'edit_etag'}),
            Mock(status_code=204),
        ]
        with pytest.raises(RuntimeError):
            with AmazonStoreEdit.transaction('client id', 'client secret', 'dummy_package_name',
                                             contact_server=True, dry_run=True):
                raise RuntimeError('oops')

        mock_http.assert_any_call(204, 'delete', 'https://developer.amazon.com/api/appstore/v1/'
                                                 'applications/dummy_package_name/edits/edit_id',
                                  headers={'If-Match': 'edit_etag'},
                                  auth=ANY)


def test_amazon_transaction_do_not_contact():
    with AmazonStoreEdit.transaction(None, None, 'dummy_package_name', contact_server=False,
                                     dry_run=True) as edit:
        assert isinstance(edit, MockAmazonStoreEdit)


def test_google_edit_resource_for_options_contact(monkeypatch):
    service_mock = MagicMock()
    service_mock.edits.return_value = 'edit resource'
    monkeypatch.setattr(store.ServiceAccountCredentials, 'from_p12_keyfile',
                        lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(store, 'build', lambda *args, **kwargs: service_mock)
    edit_resource = _create_google_edit_resource(True, 'account', 'credentials_filename')
    assert edit_resource == 'edit resource'


def test_google_edit_resource_for_options_do_not_contact():
    edit_resource = _create_google_edit_resource(False, None, None)
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
    with GooglePlayEdit.transaction(None, None, 'dummy_package_name', contact_server=False,
                                    dry_run=True) as edit:
        with pytest.raises(WrongArgumentGiven):
            edit._update_track('rollout', [1], None)


@patch.object(store, '_create_google_edit_resource')
def test_google_valid_rollout_percentage_with_track_rollout(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, None, 'dummy_package_name', contact_server=False,
                                    dry_run=True) as edit:
        edit._update_track('rollout', [1], 50)

    raw_tracks_update = mock_edits_resource.tracks().method_calls[0][2]
    assert raw_tracks_update['track'] == 'production'
    assert raw_tracks_update['body'] == {
        'releases': [{
            'status': 'inProgress',
            'userFraction': 0.5,
            'versionCodes': [1]
        }]
    }


@patch.object(store, '_create_google_edit_resource')
def test_google_valid_rollout_percentage_with_real_track(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, None, 'dummy_package_name', contact_server=False,
                                    dry_run=True) as edit:
        edit._update_track('beta', [1, 2], 20)

    raw_tracks_update = mock_edits_resource.tracks().method_calls[0][2]
    assert raw_tracks_update['track'] == 'beta'
    assert raw_tracks_update['body'] == {
        'releases': [{
            'status': 'inProgress',
            'userFraction': 0.2,
            'versionCodes': [1, 2]
        }]
    }


@patch.object(store, '_create_google_edit_resource')
def test_google_play_edit_commit_transaction(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, None, 'dummy_package_name', contact_server=False,
                                    dry_run=False) as _:
        pass

    mock_edits_resource.commit.assert_called_with(editId=ANY, packageName='dummy_package_name')


@patch.object(store, '_create_google_edit_resource')
def test_google_play_edit_no_commit_transaction(create_edit_resource):
    mock_edits_resource = MagicMock()
    create_edit_resource.return_value = mock_edits_resource
    with GooglePlayEdit.transaction(None, None, 'dummy_package_name', contact_server=False,
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
        resp={'status': str(http_status_code)},
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
        resp={'status': '403'},
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
