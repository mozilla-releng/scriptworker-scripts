import unittest
import os
import tempfile
import json
import shutil
import subprocess

from pushapkscript.script import main
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

    @unittest.mock.patch('mozapkpublisher.push_apk.PushAPK')
    def test_main_downloads_verifies_signature_and_gives_the_right_config_to_mozapkpublisher(self, PushAPK):
        with tempfile.TemporaryDirectory() as test_temp_dir:
            keystore_manager = KeystoreManager(test_temp_dir)
            keystore_manager.add_certificate(os.path.join(project_data_dir, 'android-nightly.cer'))

            config_generator = ConfigFileGenerator(test_temp_dir, keystore_manager)
            task_generator = TaskGenerator()
            task_generator.generate_file(config_generator.work_dir)

            for task_id in (task_generator.x86_task_id, task_generator.arm_task_id):
                original_path = os.path.join(test_data_dir, 'target-{}.apk'.format(task_id))
                target_path = os.path.abspath(os.path.join(test_temp_dir, 'work', 'cot', task_id, 'public/build/target.apk'))
                target_dir = os.path.dirname(target_path)
                os.makedirs(target_dir)
                shutil.copy(original_path, target_path)

            main(config_path=config_generator.generate())

            PushAPK.assert_called_with(config={
                'credentials': '/dummy/path/to/certificate.p12',
                'apk_armv7_v15': '{}/work/cot/{}/public/build/target.apk'.format(test_temp_dir, task_generator.arm_task_id),
                'apk_x86': '{}/work/cot/{}/public/build/target.apk'.format(test_temp_dir, task_generator.x86_task_id),
                'package_name': 'org.mozilla.fennec_aurora',
                'service_account': 'dummy-service-account@iam.gserviceaccount.com',
                'track': 'alpha',
                'dry_run': True,
            })
