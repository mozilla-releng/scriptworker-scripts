import unittest

import pytest
from scriptworker.exceptions import TaskVerificationError

from pushapkscript.exceptions import ConfigValidationError
from pushapkscript.googleplay import craft_push_apk_config, \
    should_commit_transaction, get_google_play_strings_path, \
    _check_google_play_string_is_the_only_failed_task, _find_unique_google_play_strings_file_in_dict


class GooglePlayTest(unittest.TestCase):
    def setUp(self):
        self.product = 'release'
        self.task_payload = {
            'google_play_track': 'alpha'
        }

        self.products = {
            'aurora': {
                'has_nightly_track': False,
                'service_account': 'aurora_account',
                'certificate': '/path/to/aurora.p12',
                'skip_check_package_names': True,
            },
            'beta': {
                'has_nightly_track': False,
                'service_account': 'beta_account',
                'certificate': '/path/to/beta.p12',
                'skip_check_package_names': True,
            },
            'release': {
                'has_nightly_track': False,
                'service_account': 'release_account',
                'certificate': '/path/to/release.p12',
                'skip_check_package_names': True,
            },
            'dep': {
                'has_nightly_track': False,
                'service_account': 'dummy_dep',
                'certificate': '/path/to/dummy_non_p12_file',
                'skip_check_package_names': True,
                'skip_check_ordered_version_codes': True,
                'skip_checks_fennec': True,
            }
        }
        self.apks = ['/path/to/x86.apk', '/path/to/arm_v15.apk']

    def test_craft_push_config(self):
        android_products = ('aurora', 'beta', 'release')
        for android_product in android_products:
            self.assertEqual(craft_push_apk_config(self.task_payload, android_product, self.products[android_product], self.apks), {
                '*args': ['/path/to/arm_v15.apk', '/path/to/x86.apk'],
                'credentials': '/path/to/{}.p12'.format(android_product),
                'commit': False,
                'no_gp_string_update': True,
                'service_account': '{}_account'.format(android_product),
                'skip_check_package_names': True,
                'track': 'alpha',
            })

    def test_craft_push_config_validates_track(self):
        task_payload_fake_track = {
            'google_play_track': 'fake'
        }

        with pytest.raises(TaskVerificationError):
            craft_push_apk_config(task_payload_fake_track, 'release', self.products['release'], self.apks)

        task_payload_nightly_track = {
            'google_play_track': 'nightly'
        }
        with pytest.raises(TaskVerificationError):
            craft_push_apk_config(task_payload_nightly_track, 'release', self.products['release'], self.apks)

        nightly_product_config = {
            'has_nightly_track': True,
            'service_account': 'release_account',
            'certificate': '/path/to/release.p12',
            'skip_check_package_names': True,
        }
        self.assertEqual(craft_push_apk_config(task_payload_nightly_track, 'release', nightly_product_config, self.apks), {
            '*args': ['/path/to/arm_v15.apk', '/path/to/x86.apk'],
            'credentials': '/path/to/release.p12',
            'commit': False,
            'no_gp_string_update': True,
            'service_account': 'release_account',
            'skip_check_package_names': True,
            'track': 'nightly',
        })

    def test_craft_push_config_allows_rollout_percentage(self):
        task_payload = {
            'google_play_track': 'rollout',
            'rollout_percentage': 10
        }
        self.assertEqual(craft_push_apk_config(task_payload, 'release', self.products['release'], self.apks), {
            '*args': ['/path/to/arm_v15.apk', '/path/to/x86.apk'],
            'credentials': '/path/to/release.p12',
            'commit': False,
            'no_gp_string_update': True,
            'rollout_percentage': 10,
            'service_account': 'release_account',
            'skip_check_package_names': True,
            'track': 'rollout',
        })

    def test_craft_push_config_allows_to_contact_google_play_or_not(self):
        config = craft_push_apk_config(self.task_payload, 'aurora', self.products['aurora'], self.apks)
        self.assertNotIn('do_not_contact_google_play', config)

        config = craft_push_apk_config(self.task_payload, 'dep', self.products['dep'], self.apks)
        self.assertTrue(config['do_not_contact_google_play'])

    def test_craft_push_config_skip_checking_multiple_locales(self):
        product_config = {
            'has_nightly_track': False,
            'service_account': 'product',
            'certificate': '/path/to/product.p12',
            'skip_check_package_names': True,
            'skip_check_multiple_locales': True,
        }
        config = craft_push_apk_config(self.task_payload, 'product', product_config, self.apks)
        self.assertIn('skip_check_multiple_locales', config)

    def test_craft_push_config_skip_checking_same_locales(self):
        product_config = {
            'has_nightly_track': False,
            'service_account': 'product',
            'certificate': '/path/to/product.p12',
            'skip_check_package_names': True,
            'skip_check_same_locales': True,
        }
        config = craft_push_apk_config(self.task_payload, 'product', product_config, self.apks)
        self.assertIn('skip_check_same_locales', config)

    def test_craft_push_config_expect_package_names(self):
        product_config = {
            'has_nightly_track': False,
            'service_account': 'product',
            'certificate': '/path/to/product.p12',
            'expected_package_names': ['org.mozilla.focus', 'org.mozilla.klar']
        }
        config = craft_push_apk_config(self.task_payload, 'product', product_config, self.apks)
        self.assertEquals(['org.mozilla.focus', 'org.mozilla.klar'], config['expected_package_names'])

    def test_craft_push_config_allows_committing_apks(self):
        task_payload = {
            'google_play_track': 'alpha',
            'commit': True
        }
        config = craft_push_apk_config(task_payload, 'release', self.products['release'], self.apks)
        self.assertTrue(config['commit'])

    def test_craft_push_config_updates_google(self):
        config = craft_push_apk_config(self.task_payload, 'release', self.products['release'], self.apks, google_play_strings_path='/path/to/google_play_strings.json')
        self.assertNotIn('no_gp_string_update', config)
        self.assertEqual(config['update_gp_strings_from_file'], '/path/to/google_play_strings.json')

    def test_should_commit_transaction(self):
        task_payload = {
            'commit': True
        }
        self.assertTrue(should_commit_transaction(task_payload))

        task_payload = {
            'commit': False
        }
        self.assertFalse(should_commit_transaction(task_payload))

        task_payload = {}
        self.assertFalse(should_commit_transaction(task_payload))

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
