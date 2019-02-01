import unittest

import pytest
from mozapkpublisher.push_apk import FileGooglePlayStrings, NoGooglePlayStrings
from scriptworker.exceptions import TaskVerificationError
from unittest.mock import MagicMock, patch, ANY

from pushapkscript.googleplay import publish_to_googleplay, get_service_account, get_certificate_path, \
    _get_play_config, should_commit_transaction, get_google_play_strings_path, \
    _check_google_play_string_is_the_only_failed_task, _find_unique_google_play_strings_file_in_dict
from pushapkscript.test.helpers.mock_file import mock_open, MockFile


@patch('pushapkscript.googleplay.open', new=mock_open)
@patch('pushapkscript.googleplay.push_apk')
class GooglePlayTest(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.context.config = {
            'google_play_accounts': {
                'aurora': {
                    'service_account': 'aurora_account',
                    'certificate': '/path/to/aurora.p12',
                },
                'beta': {
                    'service_account': 'beta_account',
                    'certificate': '/path/to/beta.p12',
                },
                'release': {
                    'service_account': 'release_account',
                    'certificate': '/path/to/release.p12',
                },
                'dep': {
                    'service_account': 'dummy_dep',
                    'certificate': '/path/to/dummy_non_p12_file',
                },
            },
            'taskcluster_scope_prefixes': ['project:releng:googleplay:'],
        }
        self.context.task = {
            'scopes': ['project:releng:googleplay:release'],
            'payload': {
                'google_play_track': 'alpha'
            },
        }
        self.apks = [MockFile('/path/to/x86.apk'), MockFile('/path/to/arm_v15.apk')]

    def test_publish_config(self, mock_push_apk):
        android_products = ('aurora', 'beta', 'release')
        for android_product in android_products:
            self.context.task['scopes'] = ['project:releng:googleplay:{}'.format(android_product)]
            publish_to_googleplay(self.context, self.apks)

            mock_push_apk.assert_called_with(
                apks=[MockFile('/path/to/x86.apk'), MockFile('/path/to/arm_v15.apk')],
                service_account='{}_account'.format(android_product),
                google_play_credentials_file=MockFile('/path/to/{}.p12'.format(android_product)),
                track='alpha',
                rollout_percentage=None,
                google_play_strings=ANY,
                commit=False,
                contact_google_play=True,
            )
            _, args = mock_push_apk.call_args
            google_play_strings = args['google_play_strings']
            assert isinstance(google_play_strings, NoGooglePlayStrings)

    def test_publish_allows_rollout_percentage(self, mock_push_apk):
        self.context.task['payload']['google_play_track'] = 'rollout'
        self.context.task['payload']['rollout_percentage'] = 10
        publish_to_googleplay(self.context, self.apks)
        mock_push_apk.assert_called_once_with(
            apks=ANY,
            service_account=ANY,
            google_play_credentials_file=ANY,
            track='rollout',
            rollout_percentage=10,
            google_play_strings=ANY,
            commit=ANY,
            contact_google_play=ANY,
        )

    def test_publish_allows_to_contact_google_play_or_not(self, mock_push_apk):
        publish_to_googleplay(self.context, self.apks)
        mock_push_apk.assert_called_with(
            apks=ANY,
            service_account=ANY,
            google_play_credentials_file=ANY,
            track=ANY,
            rollout_percentage=ANY,
            google_play_strings=ANY,
            commit=ANY,
            contact_google_play=True,
        )

        self.context.config['do_not_contact_google_play'] = True
        publish_to_googleplay(self.context, self.apks)
        mock_push_apk.assert_called_with(
            apks=ANY,
            service_account=ANY,
            google_play_credentials_file=ANY,
            track=ANY,
            rollout_percentage=ANY,
            google_play_strings=ANY,
            commit=ANY,
            contact_google_play=False,
        )

    def test_publish_allows_committing_apks(self, mock_push_apk):
        self.context.task['payload']['commit'] = True
        publish_to_googleplay(self.context, self.apks)

        mock_push_apk.assert_called_with(
            apks=ANY,
            service_account=ANY,
            google_play_credentials_file=ANY,
            track=ANY,
            rollout_percentage=ANY,
            google_play_strings=ANY,
            commit=True,
            contact_google_play=ANY,
        )

    def test_publish_raises_error_when_android_product_is_not_part_of_config(self, _):
        self.context.task['scopes'] = ['project:releng:googleplay:non_existing_android_product']
        self.assertRaises(TaskVerificationError, publish_to_googleplay, self.context, self.apks)

    def test_publish_raises_error_when_google_play_accounts_does_not_exist(self, _):
        del self.context.config['google_play_accounts']
        self.assertRaises(TaskVerificationError, publish_to_googleplay, self.context, self.apks)

    def test_publish_updates_google_strings_from_file(self, mock_push_apk):
        publish_to_googleplay(self.context, self.apks,
                              google_play_strings_file=MockFile('/path/to/google_play_strings.json'))
        _, args = mock_push_apk.call_args
        google_play_strings = args['google_play_strings']
        assert isinstance(google_play_strings, FileGooglePlayStrings)
        assert google_play_strings.file.name == '/path/to/google_play_strings.json'

    def test_get_service_account(self, _):
        self.assertEqual(get_service_account(self.context, 'aurora'), 'aurora_account')
        self.assertEqual(get_service_account(self.context, 'beta'), 'beta_account')
        self.assertEqual(get_service_account(self.context, 'release'), 'release_account')

    def test_get_certificate_path(self, _):
        self.assertEqual(get_certificate_path(self.context, 'aurora'), '/path/to/aurora.p12')
        self.assertEqual(get_certificate_path(self.context, 'beta'), '/path/to/beta.p12')
        self.assertEqual(get_certificate_path(self.context, 'release'), '/path/to/release.p12')

    def test_get_play_config(self, _):
        self.assertEqual(_get_play_config(self.context, 'aurora'), {
            'service_account': 'aurora_account', 'certificate': '/path/to/aurora.p12'
        })

        self.assertRaises(TaskVerificationError, _get_play_config, self.context, 'non-existing-android-product')

        class FakeContext:
            config = {}

        context_without_any_account = FakeContext()
        self.assertRaises(TaskVerificationError, _get_play_config, context_without_any_account, 'whatever-android-product')

    def test_should_commit_transaction(self, _):
        self.context.task['payload']['commit'] = True
        self.assertTrue(should_commit_transaction(self.context))

        self.context.task['payload']['commit'] = False
        self.assertFalse(should_commit_transaction(self.context))

        del self.context.task['payload']['commit']
        self.assertFalse(should_commit_transaction(self.context))


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
