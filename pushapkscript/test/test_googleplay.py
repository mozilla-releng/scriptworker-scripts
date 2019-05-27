import unittest

import pytest
from mozapkpublisher.push_apk import FileGooglePlayStrings, NoGooglePlayStrings
from scriptworker.exceptions import TaskVerificationError
from unittest.mock import patch, ANY

from pushapkscript.googleplay import publish_to_googleplay, \
    should_commit_transaction, get_google_play_strings_path, \
    _check_google_play_string_is_the_only_failed_task, _find_unique_google_play_strings_file_in_dict
from pushapkscript.test.helpers.mock_file import mock_open, MockFile


# TODO: refactor to pytest instead of unittest
@patch('pushapkscript.googleplay.open', new=mock_open)
@patch('pushapkscript.googleplay.push_apk')
class GooglePlayTest(unittest.TestCase):
    def setUp(self):
        self.publish_config = {
            'google_play_track': 'beta',
            'package_names': ['org.mozilla.fennec_aurora'],
            'service_account': 'service_account',
            'google_credentials_file': '/google_credentials.p12',
        }
        self.apks = [MockFile('/path/to/x86.apk'), MockFile('/path/to/arm_v15.apk')]

    def test_publish_config(self, mock_push_apk):
        publish_to_googleplay({}, {}, self.publish_config, self.apks, contact_google_play=True)

        mock_push_apk.assert_called_with(
            apks=[MockFile('/path/to/x86.apk'), MockFile('/path/to/arm_v15.apk')],
            service_account='service_account',
            google_play_credentials_file=MockFile('/google_credentials.p12'),
            track='beta',
            expected_package_names=['org.mozilla.fennec_aurora'],
            skip_check_package_names=False,
            rollout_percentage=None,
            google_play_strings=ANY,
            commit=False,
            contact_google_play=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
        )
        _, args = mock_push_apk.call_args
        assert isinstance(args['google_play_strings'], NoGooglePlayStrings)

    def test_publish_allows_rollout_percentage(self, mock_push_apk):
        publish_config = {
            'google_play_track': 'rollout',
            'rollout_percentage': 10,
            'package_names': ['org.mozilla.fennec_aurora'],
            'service_account': 'service_account',
            'google_credentials_file': '/google_credentials.p12',
        }
        publish_to_googleplay({}, {}, publish_config, self.apks, contact_google_play=True)
        _, args = mock_push_apk.call_args
        assert args['track'] == 'rollout'
        assert args['rollout_percentage'] == 10

    def test_craft_push_config_allows_to_contact_google_play_or_not(self, mock_push_apk):
        publish_to_googleplay({}, {}, self.publish_config, self.apks, contact_google_play=True)
        _, args = mock_push_apk.call_args
        assert args['contact_google_play'] is True

        publish_to_googleplay({}, {}, self.publish_config, self.apks, False)
        _, args = mock_push_apk.call_args
        assert args['contact_google_play'] is False

    def test_craft_push_config_skip_checking_multiple_locales(self, mock_push_apk):
        product_config = {
            'skip_check_multiple_locales': True,
        }
        publish_to_googleplay({}, product_config, self.publish_config, self.apks, contact_google_play=True)
        _, args = mock_push_apk.call_args
        assert args['skip_check_multiple_locales'] is True

    def test_craft_push_config_skip_checking_same_locales(self, mock_push_apk):
        product_config = {
            'skip_check_same_locales': True,
        }
        publish_to_googleplay({}, product_config, self.publish_config, self.apks, contact_google_play=True)
        _, args = mock_push_apk.call_args
        assert args['skip_check_same_locales'] is True

    def test_craft_push_config_expect_package_names(self, mock_push_apk):
        publish_config = {
            'google_play_track': 'beta',
            'package_names': ['org.mozilla.focus', 'org.mozilla.klar'],
            'service_account': 'service_account',
            'google_credentials_file': '/google_credentials.p12',
        }
        publish_to_googleplay({}, {}, publish_config, self.apks, contact_google_play=True)
        _, args = mock_push_apk.call_args
        assert args['expected_package_names'] == ['org.mozilla.focus', 'org.mozilla.klar']

    def test_craft_push_config_allows_committing_apks(self, mock_push_apk):
        task_payload = {
            'commit': True
        }
        publish_to_googleplay(task_payload, {}, self.publish_config, self.apks, contact_google_play=True)
        _, args = mock_push_apk.call_args
        assert args['commit'] is True

    def test_publish_updates_google_strings_from_file(self, mock_push_apk):
        publish_to_googleplay({}, {}, self.publish_config, self.apks, contact_google_play=True,
                              google_play_strings_file=MockFile('/path/to/google_play_strings.json'))
        _, args = mock_push_apk.call_args
        google_play_strings = args['google_play_strings']
        assert isinstance(google_play_strings, FileGooglePlayStrings)
        assert google_play_strings.file.name == '/path/to/google_play_strings.json'


def test_should_commit_transaction():
    task_payload = {
        'commit': True
    }
    assert should_commit_transaction(task_payload) is True

    task_payload = {
        'commit': False
    }
    assert should_commit_transaction(task_payload) is False

    task_payload = {}
    assert should_commit_transaction(task_payload) is False


def test_get_google_play_strings_path():
    assert get_google_play_strings_path({'someTaskId': ['/path/to/public/google_play_strings.json']}, {}) == '/path/to/public/google_play_strings.json'
    assert get_google_play_strings_path(
            {'apkTaskId': ['/path/to/public/build/target.apk']},
            {'gpStringTaskId': ['public/google_play_strings.json']}
        ) is None
    # Error cases checked in subfunctions


def test_find_unique_google_play_strings_file_in_dict():
    assert _find_unique_google_play_strings_file_in_dict({
            'apkTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/build/target.apk'],
            'someTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/google_play_strings.json'],
        }) == '/path/to/public/google_play_strings.json'

    with pytest.raises(TaskVerificationError):
        _find_unique_google_play_strings_file_in_dict({
            'apkTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/build/target.apk'],
            'someTaskId': ['public/chainOfTrust.json.asc'],
        })

    with pytest.raises(TaskVerificationError):
        _find_unique_google_play_strings_file_in_dict({
            'apkTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/build/target.apk'],
            'someTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/google_play_strings.json'],
            'someOtherTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/google_play_strings.json'],
        })


def test_check_google_play_string_is_the_only_failed_task():
    with pytest.raises(TaskVerificationError):
        _check_google_play_string_is_the_only_failed_task({
            'apkTaskId': ['/path/to/public/build/target.apk'],
            'gpStringTaskId': ['public/chainOfTrust.json.asc', 'public/google_play_strings.json']
        })

    with pytest.raises(TaskVerificationError):
        _check_google_play_string_is_the_only_failed_task({
            'missingJsonTaskId': ['public/chainOfTrust.json.asc']
        })
