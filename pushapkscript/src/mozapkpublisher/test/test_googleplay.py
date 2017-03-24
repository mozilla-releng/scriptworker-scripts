import argparse
import pytest
import random
import tempfile

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from mozapkpublisher.googleplay import add_general_google_play_arguments, EditService
from mozapkpublisher.exceptions import NoTransactionError, WrongArgumentGiven


@pytest.mark.parametrize('package_name', [
    'org.mozilla.fennec_aurora', 'org.mozilla.firefox_beta', 'org.mozilla.firefox'
])
def test_add_general_google_play_arguments(package_name):
    parser = argparse.ArgumentParser()
    add_general_google_play_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        config = parser.parse_args([
            '--package-name', package_name, '--service-account', 'dummy@dummy', '--credentials', f.name
        ])
        assert config.google_play_credentials_file.name == f.name

    assert config.package_name == package_name
    assert config.service_account == 'dummy@dummy'


def test_add_general_google_play_arguments_wrong_package():
    parser = argparse.ArgumentParser()
    add_general_google_play_arguments(parser)

    with tempfile.NamedTemporaryFile('wb') as f:
        with pytest.raises(SystemExit):
            parser.parse_args([
                '--package-name', 'wrong.package.name', '--service-account', 'dummy@dummy', '--credentials', f.name
            ])


def set_up_edit_service_mock(_monkeypatch):
    general_service_mock = MagicMock()
    edit_service_mock = MagicMock()
    new_transaction_mock = MagicMock()

    new_transaction_mock.execute = lambda: {'id': random.randint(0, 1000)}
    edit_service_mock.insert = lambda body, packageName: new_transaction_mock
    general_service_mock.edits = lambda: edit_service_mock

    _monkeypatch.setattr('mozapkpublisher.googleplay._connect', lambda _, __: general_service_mock)
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


def test_edit_service_supports_dry_run(monkeypatch):
    edit_service_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.commit_transaction()
    edit_service_mock.commit.assert_not_called()

    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name', dry_run=False)
    current_edit_id = edit_service._edit_id
    edit_service.commit_transaction()
    edit_service_mock.commit.assert_called_once_with(editId=current_edit_id, packageName='dummy_package_name')


def test_upload_apk_returns_files_metadata(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    edit_mock.apks().upload().execute.return_value = {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }
    edit_mock.apks().upload.reset_mock()

    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    response = edit_service.upload_apk(apk_path='/path/to/dummy.apk')
    assert response == {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }
    edit_mock.apks().upload.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        media_body='/path/to/dummy.apk',
    )


def test_update_track(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')

    edit_service.update_track('alpha', ['2015012345', '2015012347'])
    edit_mock.tracks().update.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        track='alpha',
        body={u'versionCodes': ['2015012345', '2015012347']}
    )

    edit_mock.tracks().update.reset_mock()
    edit_service.update_track('rollout', ['2015012345', '2015012347'], rollout_percentage=1)
    edit_mock.tracks().update.assert_called_once_with(
        editId=edit_service._edit_id,
        packageName='dummy_package_name',
        track='rollout',
        body={u'userFraction': 0.01, u'versionCodes': ['2015012345', '2015012347']}
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
