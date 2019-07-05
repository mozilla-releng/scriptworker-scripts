import argparse
import json
import pytest
import random
import tempfile

from googleapiclient.errors import HttpError
from unittest.mock import MagicMock

from mozapkpublisher.common.exceptions import NoTransactionError, WrongArgumentGiven
from mozapkpublisher.common.googleplay import add_general_google_play_arguments, EditService
from mozapkpublisher.test import does_not_raise


def test_add_general_google_play_arguments():
    parser = argparse.ArgumentParser()
    add_general_google_play_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        config = parser.parse_args([
            '--service-account', 'dummy@dummy', '--credentials', f.name
        ])
        assert config.google_play_credentials_file.name == f.name

    assert config.service_account == 'dummy@dummy'


def set_up_edit_service_mock(_monkeypatch):
    general_service_mock = MagicMock()
    edit_service_mock = MagicMock()
    new_transaction_mock = MagicMock()

    new_transaction_mock.execute = lambda: {'id': random.randint(0, 1000)}
    edit_service_mock.insert = lambda body, packageName: new_transaction_mock
    general_service_mock.edits = lambda: edit_service_mock

    _monkeypatch.setattr('mozapkpublisher.common.googleplay._connect', lambda _, __: general_service_mock)
    return edit_service_mock


def test_edit_service_starts_new_transaction_upon_init(monkeypatch):
    set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.upload_apk(apk_path='/path/to/dummy.apk')


def test_edit_service_raises_error_if_no_transaction_started(monkeypatch):
    set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.commit_transaction()
    with pytest.raises(NoTransactionError):
        edit_service.upload_apk(apk_path='/path/to/dummy.apk')


def test_edit_service_starts_new_transaction_manually(monkeypatch):
    set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    old_edit_id = edit_service._edit_id
    edit_service.commit_transaction()
    edit_service.start_new_transaction()

    assert edit_service._edit_id != old_edit_id


def test_edit_service_commits_only_when_option_is_provided(monkeypatch):
    edit_service_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.commit_transaction()
    edit_service_mock.commit.assert_not_called()

    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name', commit=True)
    current_edit_id = edit_service._edit_id
    edit_service.commit_transaction()
    edit_service_mock.commit.assert_called_once_with(editId=current_edit_id, packageName='dummy_package_name')


def test_edit_service_is_allowed_to_not_make_a_single_call_to_google_play(monkeypatch):
    edit_service_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name', commit=True, contact_google_play=False)
    edit_service.upload_apk(apk_path='/path/to/dummy.apk')
    edit_service.update_listings(
        language='some_language', title='some_title', full_description='some_description', short_description='some_desc'
    )
    edit_service.update_track(track='some_track', version_codes=['1', '2'])
    edit_service.update_whats_new(language='some_language', apk_version_code='some_version_code', whats_new='some_text')
    edit_service.commit_transaction()

    edit_service_mock.apks().upload.assert_not_called()
    edit_service_mock.apklistings().update.assert_not_called()
    edit_service_mock.tracks().update.assert_not_called()
    edit_service_mock.apklistings().update.assert_not_called()
    edit_service_mock.commit.assert_not_called()


def test_get_track_status(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
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

    edit_mock.tracks().get().execute.return_value = release_data

    edit_mock.tracks().get.reset_mock()

    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    assert edit_service.get_track_status(track='production') == release_data
    edit_mock.tracks().get.assert_called_once_with(
        editId=edit_service._edit_id,
        track='production',
        packageName='dummy_package_name',
    )


def test_upload_apk_returns_files_metadata(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    edit_mock.apks().upload().execute.return_value = {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }
    edit_mock.apks().upload.reset_mock()

    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.upload_apk(apk_path='/path/to/dummy.apk')
    edit_mock.apks().upload.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        media_body='/path/to/dummy.apk',
    )


@pytest.mark.parametrize('http_status_code', (400, 403))
def test_upload_apk_errors_out(monkeypatch, http_status_code):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    edit_mock.apks().upload().execute.side_effect = HttpError(
        # XXX status is presented as a string by googleapiclient
        resp={'status': str(http_status_code)},
        # XXX content must be bytes
        # https://github.com/googleapis/google-api-python-client/blob/ffea1a7fe9d381d23ab59048263c631cc2b45323/googleapiclient/errors.py#L41
        content=b'{"error": {"errors": [{"reason": "someRandomReason"}] } }',
    )
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')

    with pytest.raises(HttpError):
        edit_service.upload_apk(apk_path='/path/to/dummy.apk')


@pytest.mark.parametrize('reason, expectation', (
    ('apkUpgradeVersionConflict', does_not_raise()),
    ('apkNotificationMessageKeyUpgradeVersionConflict', does_not_raise()),
    ('someRandomReason', pytest.raises(HttpError)),
))
def test_upload_apk_does_not_error_out_when_apk_is_already_published(monkeypatch, reason, expectation):
    edit_mock = set_up_edit_service_mock(monkeypatch)
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

    edit_mock.apks().upload().execute.side_effect = HttpError(
        # XXX status is presented as a string by googleapiclient
        resp={'status': '403'},
        content=content_bytes,
    )
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')

    with expectation:
        edit_service.upload_apk(apk_path='/path/to/dummy.apk')


def test_update_track(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')

    edit_service.update_track('alpha', ['2015012345', '2015012347'])
    edit_mock.tracks().update.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        track='alpha',
        body={
            'releases': [{
                'status': 'completed',
                'versionCodes': ['2015012345', '2015012347'],
            }],
        },
    )

    edit_mock.tracks().update.reset_mock()
    edit_service.update_track('rollout', ['2015012345', '2015012347'], rollout_percentage=1)
    edit_mock.tracks().update.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        track='rollout',
        body={
            'releases': [{
                'status': 'completed',
                'versionCodes': ['2015012345', '2015012347']},
            ],
            'userFraction': 0.01,
        },
    )


@pytest.mark.parametrize('invalid_percentage', (-1, 101))
def test_update_track_should_refuse_wrong_percentage(monkeypatch, invalid_percentage):
    set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')

    with pytest.raises(WrongArgumentGiven):
        edit_service.update_track('rollout', ['2015012345', '2015012347'], invalid_percentage)


def test_update_listings(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')

    edit_service.update_listings(
        'en-GB',
        title='Firefox for Android Beta',
        full_description='Long description',
        short_description='Short',
    )
    edit_mock.listings().update.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        language='en-GB',
        body={
            'title': 'Firefox for Android Beta',
            'fullDescription': 'Long description',
            'shortDescription': 'Short',
        }
    )


def test_update_whats_new(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')

    edit_service.update_whats_new('en-GB', '2015012345', 'Check out this cool feature!')
    edit_mock.apklistings().update.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        language='en-GB',
        apkVersionCode='2015012345',
        body={'recentChanges': 'Check out this cool feature!'}
    )
