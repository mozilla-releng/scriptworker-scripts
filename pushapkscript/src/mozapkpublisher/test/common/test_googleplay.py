import argparse
import json

from mock import ANY, patch
import pytest
import random
import tempfile

from googleapiclient.errors import HttpError
from unittest.mock import MagicMock

from mozapkpublisher.common import googleplay
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.googleplay import add_general_google_play_arguments, \
    GooglePlayEdit, edit_resource_for_options
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


def test_edit_resource_for_options_do_not_contact():
    edit_resource = edit_resource_for_options(False, '', MagicMock)
    assert isinstance(edit_resource, MagicMock)


@pytest.fixture
def edit_resource_mock():
    edit_resource = MagicMock()
    new_transaction_mock = MagicMock()

    new_transaction_mock.execute = lambda: {'id': random.randint(0, 1000)}
    edit_resource.insert = lambda body, packageName: new_transaction_mock
    return edit_resource


@patch.object(googleplay, 'edit_resource_for_options')
def test_google_play_edit_no_commit_transaction(edit_resource_for_options_):
    mock_edits_resource = MagicMock()
    edit_resource_for_options_.return_value = mock_edits_resource
    with googleplay.edit(None, None, 'package.name', contact_google_play=False, commit=False) as _:
        pass

    mock_edits_resource.commit.assert_not_called()


@patch.object(googleplay, 'edit_resource_for_options')
def test_google_play_edit_commit_transaction(edit_resource_for_options_):
    mock_edits_resource = MagicMock()
    edit_resource_for_options_.return_value = mock_edits_resource
    with googleplay.edit(None, None, 'package.name', contact_google_play=False, commit=True) as _:
        pass

    mock_edits_resource.commit.assert_called_with(editId=ANY, packageName='package.name')


def test_get_track_status(edit_resource_mock):
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


def test_upload_apk_returns_files_metadata(edit_resource_mock):
    edit_resource_mock.apks().upload().execute.return_value = {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }
    edit_resource_mock.apks().upload.reset_mock()

    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')
    google_play.upload_apk(apk_path='/path/to/dummy.apk')
    edit_resource_mock.apks().upload.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        media_body='/path/to/dummy.apk',
    )


@pytest.mark.parametrize('http_status_code', (400, 403))
def test_upload_apk_errors_out(edit_resource_mock, http_status_code):
    edit_resource_mock.apks().upload().execute.side_effect = HttpError(
        # XXX status is presented as a string by googleapiclient
        resp={'status': str(http_status_code)},
        # XXX content must be bytes
        # https://github.com/googleapis/google-api-python-client/blob/ffea1a7fe9d381d23ab59048263c631cc2b45323/googleapiclient/errors.py#L41
        content=b'{"error": {"errors": [{"reason": "someRandomReason"}] } }',
    )
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    with pytest.raises(HttpError):
        google_play.upload_apk(apk_path='/path/to/dummy.apk')


@pytest.mark.parametrize('reason, expectation', (
    ('apkUpgradeVersionConflict', does_not_raise()),
    ('apkNotificationMessageKeyUpgradeVersionConflict', does_not_raise()),
    ('someRandomReason', pytest.raises(HttpError)),
))
def test_upload_apk_does_not_error_out_when_apk_is_already_published(edit_resource_mock, reason, expectation):
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
        google_play.upload_apk(apk_path='/path/to/dummy.apk')


def test_update_track(edit_resource_mock):
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    google_play.update_track('alpha', ['2015012345', '2015012347'])
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
    google_play.update_track('production', ['2015012345', '2015012347'], rollout_percentage=1)
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
def test_update_track_should_refuse_wrong_percentage(edit_resource_mock, invalid_percentage):
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    with pytest.raises(WrongArgumentGiven):
        google_play.update_track('production', ['2015012345', '2015012347'], invalid_percentage)


def test_update_listings(edit_resource_mock):
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


def test_update_whats_new(edit_resource_mock):
    google_play = GooglePlayEdit(edit_resource_mock, 1, 'dummy_package_name')

    google_play.update_whats_new('en-GB', '2015012345', 'Check out this cool feature!')
    edit_resource_mock.apklistings().update.assert_called_once_with(
        editId=google_play._edit_id,
        packageName='dummy_package_name',
        language='en-GB',
        apkVersionCode='2015012345',
        body={'recentChanges': 'Check out this cool feature!'}
    )
