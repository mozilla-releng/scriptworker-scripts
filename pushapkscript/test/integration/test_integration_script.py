import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from pushapkscript.script import sync_main, async_main
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
            json.dump(self._generate_json(), f)
        return self.config_file

    def _generate_json(self):
        return json.loads('''{{
            "work_dir": "{work_dir}",
            "schema_file": "{project_data_dir}/pushapk_task_schema.json",
            "verbose": true,

            "jarsigner_key_store": "{keystore_path}",
            "jarsigner_certificate_alias": "{certificate_alias}",
            "google_play_accounts": {{
                "aurora": {{
                    "service_account": "dummy-service-account@iam.gserviceaccount.com",
                    "certificate": "/dummy/path/to/certificate.p12"
                }}
            }}
        }}'''.format(
            work_dir=self.work_dir, test_data_dir=self.test_data_dir, project_data_dir=project_data_dir,
            keystore_path=self.keystore_manager.keystore_path,
            certificate_alias=self.keystore_manager.certificate_alias
        ))


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

    @unittest.mock.patch('mozapkpublisher.push_apk.PushAPK')
    def test_main_downloads_verifies_signature_and_gives_the_right_config_to_mozapkpublisher(self, PushAPK):
        task_generator = TaskGenerator()
        task_generator.generate_file(self.config_generator.work_dir)

        self._copy_all_apks_to_test_temp_dir(task_generator)
        sync_main(async_main, config_path=self.config_generator.generate())

        PushAPK.assert_called_with(config={
            'credentials': '/dummy/path/to/certificate.p12',
            'apk_armv7_v15': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id),
            'apk_x86': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id),
            'commit': False,
            'credentials': '/dummy/path/to/certificate.p12',
            'no_gp_string_update': True,
            'package_name': 'org.mozilla.fennec_aurora',
            'service_account': 'dummy-service-account@iam.gserviceaccount.com',
            'track': 'alpha',
        })

    @unittest.mock.patch('mozapkpublisher.push_apk.PushAPK')
    def test_main_allows_rollout_percentage(self, PushAPK):
        task_generator = TaskGenerator(google_play_track='rollout', rollout_percentage=25)
        task_generator.generate_file(self.config_generator.work_dir)

        self._copy_all_apks_to_test_temp_dir(task_generator)
        sync_main(async_main, config_path=self.config_generator.generate())

        PushAPK.assert_called_with(config={
            'credentials': '/dummy/path/to/certificate.p12',
            'apk_armv7_v15': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id),
            'apk_x86': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id),
            'credentials': '/dummy/path/to/certificate.p12',
            'commit': False,
            'no_gp_string_update': True,
            'package_name': 'org.mozilla.fennec_aurora',
            'rollout_percentage': 25,
            'service_account': 'dummy-service-account@iam.gserviceaccount.com',
            'track': 'rollout',
        })

    @unittest.mock.patch('mozapkpublisher.push_apk.PushAPK')
    def test_main_allows_google_play_strings_file_and_commit_transaction(self, PushAPK):
        task_generator = TaskGenerator(should_commit_transaction=True)
        task_generator.generate_file(self.config_generator.work_dir)

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self._copy_single_file_to_test_temp_dir(
            task_id=task_generator.google_play_strings_task_id,
            origin_file_name='google_play_strings.json',
            destination_path='public/google_play_strings.json',
        )
        sync_main(async_main, config_path=self.config_generator.generate())

        PushAPK.assert_called_with(config={
            'apk_armv7_v15': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id),
            'apk_x86': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id),
            'credentials': '/dummy/path/to/certificate.p12',
            'commit': True,
            'package_name': 'org.mozilla.fennec_aurora',
            'service_account': 'dummy-service-account@iam.gserviceaccount.com',
            'track': 'alpha',
            'update_gp_strings_from_file': '{}/work/cot/{}/public/google_play_strings.json'.format(
                self.test_temp_dir, task_generator.google_play_strings_task_id
            ),
        })

    @unittest.mock.patch('mozapkpublisher.push_apk.PushAPK')
    def test_main_still_supports_old_task_def(self, PushAPK):
        task_generator = TaskGenerator(task_def_before_firefox_59=True, should_commit_transaction=True)
        task_generator.generate_file(self.config_generator.work_dir)

        self._copy_all_apks_to_test_temp_dir(task_generator)
        sync_main(async_main, config_path=self.config_generator.generate())

        PushAPK.assert_called_with(config={
            'apk_armv7_v15': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id),
            'apk_x86': '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id),
            'credentials': '/dummy/path/to/certificate.p12',
            'commit': True,
            'package_name': 'org.mozilla.fennec_aurora',
            'service_account': 'dummy-service-account@iam.gserviceaccount.com',
            'track': 'alpha',
            'update_gp_strings_from_l10n_store': True,
        })
