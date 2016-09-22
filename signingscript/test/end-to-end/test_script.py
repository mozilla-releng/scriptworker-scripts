import unittest
import os
import shutil
import tempfile
import json
import subprocess

from signingscript.script import main

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


class GooglePlayManager(object):
    def __init__(self, test_data_dir):
        self.certificate_file = os.path.join(test_data_dir, 'googleplay.p12')
        shutil.copy(
            os.path.join(project_dir, 'signingscript', 'data', 'googleplay.p12'),
            self.certificate_file
        )


class ConfigFileGenerator(object):
    def __init__(self, test_data_dir, keystore_manager, google_play_manager):
        self.test_data_dir = test_data_dir
        self.keystore_manager = keystore_manager
        self.google_play_manager = google_play_manager
        self.config_file = os.path.join(self.test_data_dir, 'config.json')

        self.work_dir = os.path.join(test_data_dir, 'work')
        os.mkdir(self.work_dir)

    def generate(self):
        with open(self.config_file, 'w') as f:
            json.dump(self._generate_json(), f)
        return self.config_file

    def _generate_json(self):
        # TODO Change service_account
        return json.loads('''{{
            "work_dir": "{work_dir}",
            "schema_file": "{project_dir}/signingscript/data/signing_task_schema.json",
            "verbose": true,

            "google_play_service_account": "a-service-account@.iam.gserviceaccount.com",
            "google_play_certificate": "{google_play_certificate_path}",
            "google_play_package_name": "org.mozilla.fennec_aurora",

            "jarsigner_key_store": "{keystore_path}",
            "jarsigner_certificate_alias": "{certificate_alias}"
        }}'''.format(
            work_dir=self.work_dir, test_data_dir=self.test_data_dir, project_dir=project_dir,
            google_play_certificate_path=self.google_play_manager.certificate_file,
            keystore_path=self.keystore_manager.keystore_path,
            certificate_alias=self.keystore_manager.certificate_alias
        ))


class TaskFileGenerator(object):
    def __init__(self, work_dir):
        self.task_file = os.path.join(work_dir, 'task.json')

    def generate(self):
        with open(self.task_file, 'w') as f:
            json.dump(self._generate_json(), f)
        return self.task_file

    def _generate_json(self):
        return json.loads('''{
          "provisionerId": "meh",
          "workerType": "workertype",
          "schedulerId": "task-graph-scheduler",
          "taskGroupId": "some",
          "routes": [],
          "retries": 5,
          "created": "2015-05-08T16:15:58.903Z",
          "deadline": "2015-05-08T18:15:59.010Z",
          "expires": "2016-05-08T18:15:59.010Z",
          "dependencies": ["DIYnEVJ_SaSLGWtd3_n3VA", "EZJ0suL7St65V_MM0iBhKw"],
          "scopes": ["signing"],
          "payload": {
            "apks": {
              "armv7_v15": "https://queue.taskcluster.net/v1/task/DIYnEVJ_SaSLGWtd3_n3VA/artifacts/public%2Fbuild%2Ffennec-46.0a2.en-US.android-arm.apk",
              "x86": "https://queue.taskcluster.net/v1/task/EZJ0suL7St65V_MM0iBhKw/artifacts/public%2Fbuild%2Ffennec-46.0a2.en-US.android-i386.apk"
            },
            "google_play_track": "alpha"
          }
        }''')


class MainTest(unittest.TestCase):

    def test_validate_task(self):
        with tempfile.TemporaryDirectory() as test_data_dir:
            keystore_manager = KeystoreManager(test_data_dir)
            keystore_manager.add_certificate('/home/jlorenzo/git/mozilla-releng/private/passwords/android-nightly.cer')

            google_play_manager = GooglePlayManager(test_data_dir)

            config_generator = ConfigFileGenerator(test_data_dir, keystore_manager, google_play_manager)
            task_generator = TaskFileGenerator(config_generator.work_dir)
            task_generator.generate()

            main(config_path=config_generator.generate())
