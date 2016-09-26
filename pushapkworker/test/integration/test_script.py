import unittest
import os
import tempfile
import json
import subprocess

from pushapkworker.script import main
from pushapkworker.test.helpers.task_generator import TaskGenerator

this_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.join(this_dir, '..', '..', '..')


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
            "schema_file": "{project_dir}/pushapkworker/data/signing_task_schema.json",
            "verbose": true,

            "google_play_service_account": "a-service-account@.iam.gserviceaccount.com",
            "google_play_certificate": "/dummy/path/to/certificate.p12",
            "google_play_package_name": "org.mozilla.fennec_aurora",

            "jarsigner_key_store": "{keystore_path}",
            "jarsigner_certificate_alias": "{certificate_alias}"
        }}'''.format(
            work_dir=self.work_dir, test_data_dir=self.test_data_dir, project_dir=project_dir,
            keystore_path=self.keystore_manager.keystore_path,
            certificate_alias=self.keystore_manager.certificate_alias
        ))


class MainTest(unittest.TestCase):

    @unittest.mock.patch('mozapkpublisher.push_apk.PushAPK')
    @unittest.skipIf(os.environ.get('RUN_NETWORK_TESTS') != 1, 'Tests requiring network are skipped')
    def test_main_downloads_verifies_signature_and_gives_the_right_config_to_mozapkpublisher(self, PushAPK):
        with tempfile.TemporaryDirectory() as test_data_dir:
            keystore_manager = KeystoreManager(test_data_dir)
            # TODO Download the certificate once it's public
            keystore_manager.add_certificate('/home/jlorenzo/git/mozilla-releng/private/passwords/android-nightly.cer')

            config_generator = ConfigFileGenerator(test_data_dir, keystore_manager)
            task_generator = TaskGenerator()
            task_generator.generate_file(config_generator.work_dir)

            main(config_path=config_generator.generate())

            PushAPK.assert_called_with(config={
                'credentials': '/dummy/path/to/certificate.p12',
                'apk_armv7_v15': '{}/work/public/build/fennec-46.0a2.en-US.android-arm.apk'.format(test_data_dir),
                'apk_x86': '{}/work/public/build/fennec-46.0a2.en-US.android-i386.apk'.format(test_data_dir),
                'package_name': 'org.mozilla.fennec_aurora',
                'service_account': 'a-service-account@.iam.gserviceaccount.com',
                'track': 'alpha'
            })
