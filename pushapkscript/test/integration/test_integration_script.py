import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from mozapkpublisher.push_apk import NoGooglePlayStrings, FileGooglePlayStrings

from pushapkscript.script import main
from pushapkscript.test.helpers.mock_file import mock_open, MockFile
from pushapkscript.test.helpers.task_generator import TaskGenerator

this_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.join(this_dir, '..', '..', '..')
project_data_dir = os.path.join(project_dir, 'pushapkscript', 'data')
test_data_dir = os.path.join(this_dir, '..', 'data')


class KeystoreManager(object):
    def __init__(self, test_data_dir, certificate_alias='nightly', keystore_password='12345678'):
        self.keystore_path = os.path.join(test_data_dir, 'keystore')
        self.certificate_alias = certificate_alias
        self.keystore_password = keystore_password

    def add_certificate(self, certificate_path):
        subprocess.run([
            'keytool', '-import', '-noprompt',
            '-keystore', self.keystore_path, '-storepass', self.keystore_password,
            '-file', certificate_path, '-alias', self.certificate_alias
        ])


class ConfigFileGenerator(object):
    def __init__(self, test_data_dir, keystore_manager):
        self.test_data_dir = test_data_dir
        self.keystore_manager = keystore_manager
        self.config_file = os.path.join(self.test_data_dir, 'config.json')

        self.work_dir = os.path.join(test_data_dir, 'work')
        os.mkdir(self.work_dir)

    def generate(self):
        with open(self.config_file, 'w') as f:
            json.dump(self._generate_config(), f)
        return self.config_file

    def _generate_config(self):
        work_dir = self.work_dir
        keystore_path = self.keystore_manager.keystore_path
        certificate_alias = self.keystore_manager.certificate_alias
        return {
            "work_dir": work_dir,
            "verbose": True,

            "jarsigner_key_store": keystore_path,
            "jarsigner_certificate_alias": certificate_alias,
            "products": {
                "aurora": {
                    "digest_algorithm": "SHA1",
                    "service_account": "dummy-service-account@iam.gserviceaccount.com",
                    "certificate": "/dummy/path/to/certificate.p12",
                    "has_nightly_track": False,
                    "skip_check_package_names": False,
                    "update_google_play_strings": True,
                    "expected_package_names": ["org.mozilla.fennec_aurora"]
                }
            },
            "taskcluster_scope_prefixes": ["project:releng:googleplay:"]
        }


@unittest.mock.patch('pushapkscript.script.open', new=mock_open)
@unittest.mock.patch('pushapkscript.googleplay.open', new=mock_open)
class MainTest(unittest.TestCase):

    def setUp(self):
        self.test_temp_dir_fp = tempfile.TemporaryDirectory()
        self.test_temp_dir = self.test_temp_dir_fp.name
        self.keystore_manager = KeystoreManager(self.test_temp_dir)
        self.keystore_manager.add_certificate(os.path.join(project_data_dir, 'android-nightly.cer'))

        self.config_generator = ConfigFileGenerator(self.test_temp_dir, self.keystore_manager)

        # Workaround event loop being closed
        policy = asyncio.get_event_loop_policy()
        self.event_loop = policy.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        self.event_loop._close = self.event_loop.close
        self.event_loop.close = lambda: None

    def tearDown(self):
        self.test_temp_dir_fp.cleanup()

    def _copy_all_apks_to_test_temp_dir(self, task_generator):
        for task_id in (task_generator.x86_task_id, task_generator.arm_task_id):
            self._copy_single_file_to_test_temp_dir(
                task_id,
                origin_file_name='target-{}.apk'.format(task_id),
                destination_path='public/build/target.apk'
            )

    def _copy_single_file_to_test_temp_dir(self, task_id, origin_file_name, destination_path):
        original_path = os.path.join(test_data_dir, origin_file_name)
        target_path = os.path.abspath(os.path.join(self.test_temp_dir, 'work', 'cot', task_id, destination_path))
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir)
        shutil.copy(original_path, target_path)

    @unittest.mock.patch('pushapkscript.googleplay.push_apk')
    def test_main_downloads_verifies_signature_and_gives_the_right_config_to_mozapkpublisher(self, push_apk):
        task_generator = TaskGenerator()
        task_generator.generate_file(self.config_generator.work_dir)

        self._copy_all_apks_to_test_temp_dir(task_generator)
        main(config_path=self.config_generator.generate())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='dummy-service-account@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/dummy/path/to/certificate.p12'),
            track='alpha',
            expected_package_names=['org.mozilla.fennec_aurora'],
            skip_check_package_names=False,
            rollout_percentage=None,
            google_play_strings=unittest.mock.ANY,
            commit=False,
            contact_google_play=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
        )
        _, args = push_apk.call_args
        assert isinstance(args['google_play_strings'], NoGooglePlayStrings)

    @unittest.mock.patch('pushapkscript.googleplay.push_apk')
    def test_main_allows_rollout_percentage(self, push_apk):
        task_generator = TaskGenerator(google_play_track='rollout', rollout_percentage=25)
        task_generator.generate_file(self.config_generator.work_dir)

        self._copy_all_apks_to_test_temp_dir(task_generator)
        main(config_path=self.config_generator.generate())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='dummy-service-account@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/dummy/path/to/certificate.p12'),
            track='rollout',
            expected_package_names=['org.mozilla.fennec_aurora'],
            skip_check_package_names=False,
            rollout_percentage=25,
            google_play_strings=unittest.mock.ANY,
            commit=False,
            contact_google_play=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
        )
        _, args = push_apk.call_args
        assert isinstance(args['google_play_strings'], NoGooglePlayStrings)

    @unittest.mock.patch('pushapkscript.googleplay.push_apk')
    def test_main_allows_google_play_strings_file_and_commit_transaction(self, push_apk):
        task_generator = TaskGenerator(should_commit_transaction=True)
        task_generator.generate_file(self.config_generator.work_dir)

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self._copy_single_file_to_test_temp_dir(
            task_id=task_generator.google_play_strings_task_id,
            origin_file_name='google_play_strings.json',
            destination_path='public/google_play_strings.json',
        )
        main(config_path=self.config_generator.generate())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='dummy-service-account@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/dummy/path/to/certificate.p12'),
            track='alpha',
            expected_package_names=['org.mozilla.fennec_aurora'],
            skip_check_package_names=False,
            rollout_percentage=None,
            google_play_strings=unittest.mock.ANY,
            commit=True,
            contact_google_play=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
        )
        _, args = push_apk.call_args
        google_play_strings = args['google_play_strings']
        assert isinstance(google_play_strings, FileGooglePlayStrings)
        assert google_play_strings.file.name == '{}/work/cot/{}/public/google_play_strings.json'.format(
                self.test_temp_dir, task_generator.google_play_strings_task_id
            )
