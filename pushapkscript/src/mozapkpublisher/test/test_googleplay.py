import argparse
import pytest
import tempfile

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from mozapkpublisher.googleplay import add_general_google_play_arguments, EditService
from mozapkpublisher.exceptions import NoTransactionError


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
    general_service_mock.edits = lambda: edit_service_mock

    _monkeypatch.setattr('mozapkpublisher.googleplay._connect', lambda _, __: general_service_mock)
    return edit_service_mock


def test_edit_service_starts_new_transaction(monkeypatch):
    set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.upload_apk(apk_path='/path/to/dummy.apk')


def test_edit_service_supports_dry_run(monkeypatch):
    edit_service_mock = set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.commit_transaction()
    edit_service_mock.commit.assert_not_called()

    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name', dry_run=False)
    current_edit_id = edit_service._edit_id
    edit_service.commit_transaction()
    edit_service_mock.commit.assert_called_once_with(editId=current_edit_id, packageName='dummy_package_name')


def test_edit_service_raises_error_if_no_transaction_started(monkeypatch):
    set_up_edit_service_mock(monkeypatch)
    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    edit_service.commit_transaction()
    with pytest.raises(NoTransactionError):
        edit_service.upload_apk(apk_path='/path/to/dummy.apk')


def test_upload_apk_returns_files_metadata(monkeypatch):
    edit_mock = set_up_edit_service_mock(monkeypatch)
    upload_mock = MagicMock()
    upload_mock.execute = lambda: {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }

    apks_mock = MagicMock()
    apks_mock.upload = lambda editId, packageName, media_body: upload_mock
    edit_mock.apks = lambda: apks_mock

    edit_service = EditService('service_account', 'credentials_file_path', 'dummy_package_name')
    response = edit_service.upload_apk(apk_path='/path/to/dummy.apk')
    assert response == {
        'binary': {'sha1': '1234567890abcdef1234567890abcdef12345678'}, 'versionCode': 2015012345
    }
