import unittest

from scriptworker.exceptions import TaskVerificationError
from unittest.mock import MagicMock

from pushapkscript.googleplay import craft_push_apk_config, get_service_account, get_certificate_path, \
    _get_play_config, should_commit_transaction, get_google_play_strings_path, \
    _check_google_play_string_is_the_only_failed_task, _find_unique_google_play_strings_file_in_dict


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
            'taskcluster_scope_prefix': 'project:releng:googleplay:',
        }
        self.context.task = {
            'scopes': ['project:releng:googleplay:release'],
            'payload': {
                'google_play_track': 'alpha'
            },
        }
        self.apks = ['/path/to/x86.apk', '/path/to/arm_v15.apk']

    def test_craft_push_config(self):
        android_products = ('aurora', 'beta', 'release')
        for android_product in android_products:
            self.context.task['scopes'] = ['project:releng:googleplay:{}'.format(android_product)]
            self.assertEqual(craft_push_apk_config(self.context, self.apks), {
                '*args': ['/path/to/arm_v15.apk', '/path/to/x86.apk'],
                'credentials': '/path/to/{}.p12'.format(android_product),
                'commit': False,
                'no_gp_string_update': True,
                'service_account': '{}_account'.format(android_product),
                'track': 'alpha',
            })

    def test_craft_push_config_allows_rollout_percentage(self):
        self.context.task['payload']['google_play_track'] = 'rollout'
        self.context.task['payload']['rollout_percentage'] = 10
        self.assertEqual(craft_push_apk_config(self.context, self.apks), {
            '*args': ['/path/to/arm_v15.apk', '/path/to/x86.apk'],
            'credentials': '/path/to/release.p12',
            'commit': False,
            'no_gp_string_update': True,
            'rollout_percentage': 10,
            'service_account': 'release_account',
            'track': 'rollout',
        })

    def test_craft_push_config_allows_to_contact_google_play_or_not(self):
        self.context.task['scopes'] = ['project:releng:googleplay:aurora']
        config = craft_push_apk_config(self.context, self.apks)
        self.assertNotIn('do_not_contact_google_play', config)

        self.context.task['scopes'] = ['project:releng:googleplay:dep']
        config = craft_push_apk_config(self.context, self.apks)
        self.assertTrue(config['do_not_contact_google_play'])

    def test_craft_push_config_allows_committing_apks(self):
        self.context.task['scopes'] = ['project:releng:googleplay:aurora']
        self.context.task['payload']['commit'] = True
        config = craft_push_apk_config(self.context, self.apks)
        self.assertTrue(config['commit'])

    def test_craft_push_config_raises_error_when_android_product_is_not_part_of_config(self):
        self.context.task['scopes'] = ['project:releng:googleplay:non_exiting_android_product']
        self.assertRaises(TaskVerificationError, craft_push_apk_config, self.context, self.apks)

    def test_craft_push_config_raises_error_when_google_play_accounts_does_not_exist(self):
        del self.context.config['google_play_accounts']
        self.assertRaises(TaskVerificationError, craft_push_apk_config, self.context, self.apks)

    def test_craft_push_config_updates_google(self):
        config = craft_push_apk_config(self.context, self.apks, google_play_strings_path='/path/to/google_play_strings.json')
        self.assertNotIn('no_gp_string_update', config)
        self.assertEqual(config['update_gp_strings_from_file'], '/path/to/google_play_strings.json')

    def test_get_service_account(self):
        self.assertEqual(get_service_account(self.context, 'aurora'), 'aurora_account')
        self.assertEqual(get_service_account(self.context, 'beta'), 'beta_account')
        self.assertEqual(get_service_account(self.context, 'release'), 'release_account')

    def test_get_certificate_path(self):
        self.assertEqual(get_certificate_path(self.context, 'aurora'), '/path/to/aurora.p12')
        self.assertEqual(get_certificate_path(self.context, 'beta'), '/path/to/beta.p12')
        self.assertEqual(get_certificate_path(self.context, 'release'), '/path/to/release.p12')

    def test_get_play_config(self):
        self.assertEqual(_get_play_config(self.context, 'aurora'), {
            'service_account': 'aurora_account', 'certificate': '/path/to/aurora.p12'
        })

        self.assertRaises(TaskVerificationError, _get_play_config, self.context, 'non-existing-android-product')

        class FakeContext:
            config = {}

        context_without_any_account = FakeContext()
        self.assertRaises(TaskVerificationError, _get_play_config, context_without_any_account, 'whatever-android-product')

    def test_should_commit_transaction(self):
        self.context.task['payload']['commit'] = True
        self.assertTrue(should_commit_transaction(self.context))

        self.context.task['payload']['commit'] = False
        self.assertFalse(should_commit_transaction(self.context))

        del self.context.task['payload']['commit']
        self.assertFalse(should_commit_transaction(self.context))

    def test_get_google_play_strings_path(self):
        self.assertEqual(
            get_google_play_strings_path({'someTaskId': ['/path/to/public/google_play_strings.json']}, {}),
            '/path/to/public/google_play_strings.json'
        )
        self.assertEqual(
            get_google_play_strings_path(
                {'apkTaskId': ['/path/to/public/build/target.apk']},
                {'gpStringTaskId': ['public/google_play_strings.json']}
            ),
            None
        )
        # Error cases checked in subfunctions

    def test_check_google_play_string_is_the_only_failed_task(self):
        with self.assertRaises(TaskVerificationError):
            _check_google_play_string_is_the_only_failed_task({
                'apkTaskId': ['/path/to/public/build/target.apk'],
                'gpStringTaskId': ['public/chainOfTrust.json.asc', 'public/google_play_strings.json']
            })

        with self.assertRaises(TaskVerificationError):
            _check_google_play_string_is_the_only_failed_task({
                'missingJsonTaskId': ['public/chainOfTrust.json.asc']
            })

    def test_find_unique_google_play_strings_file_in_dict(self):
        self.assertEqual(
            _find_unique_google_play_strings_file_in_dict({
                'apkTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/build/target.apk'],
                'someTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/google_play_strings.json'],
            }),
            '/path/to/public/google_play_strings.json'
        )

        with self.assertRaises(TaskVerificationError):
            _find_unique_google_play_strings_file_in_dict({
                'apkTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/build/target.apk'],
                'someTaskId': ['public/chainOfTrust.json.asc'],
            })

        with self.assertRaises(TaskVerificationError):
            _find_unique_google_play_strings_file_in_dict({
                'apkTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/build/target.apk'],
                'someTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/google_play_strings.json'],
                'someOtherTaskId': ['public/chainOfTrust.json.asc', '/path/to/public/google_play_strings.json'],
            })
