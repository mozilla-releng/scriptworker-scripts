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
    def __init__(self, test_data_dir, project_data_dir):
        self.keystore_path = os.path.join(test_data_dir, 'keystore')
        self.project_data_dir = project_data_dir
        self.keystore_password = '12345678'

    def add_certificate(self, certificate_alias):
        subprocess.run([
            'keytool', '-import', '-noprompt',
            # JDK 9 changes default type to PKCS12, which causes "jarsigner -verify" to fail
            '-storetype', 'jks',
            '-keystore', self.keystore_path, '-storepass', self.keystore_password,
            '-file', os.path.join(self.project_data_dir, 'android-nightly.cer'), '-alias', certificate_alias
        ])


class ConfigFileGenerator(object):
    def __init__(self, test_data_dir, keystore_manager):
        self.test_data_dir = test_data_dir
        self.keystore_manager = keystore_manager
        self.config_file = os.path.join(self.test_data_dir, 'config.json')

        self.work_dir = os.path.join(test_data_dir, 'work')
        os.mkdir(self.work_dir)

    def write_config(self, config):
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        return self.config_file

    def generate_fennec_config(self):
        work_dir = self.work_dir
        keystore_path = self.keystore_manager.keystore_path
        return self.write_config({
            "work_dir": work_dir,
            "verbose": True,

            "jarsigner_key_store": keystore_path,
            "products": [{
                "product_names": ["aurora", "beta", "release"],
                "update_google_play_strings": True,
                "digest_algorithm": "SHA1",
                "skip_check_package_names": True,
                "use_scope_for_channel": True,
                "map_channels_to_apps": True,
                "apps": {
                    "aurora": {
                        "package_names": ["org.mozilla.fennec_aurora"],
                        "google_play_track": "beta",
                        "service_account": "firefox-aurora@iam.gserviceaccount.com",
                        "google_credentials_file": "/firefox-nightly.p12",
                        "certificate_alias": "nightly",
                    },
                    "beta": {
                        "package_names": ["org.mozilla.firefox_beta"],
                        "google_play_track": "production",
                        "service_account": "firefox-beta@iam.gserviceaccount.com",
                        "google_credentials_file": "/firefox.p12",
                        "certificate_alias": "release",
                    },
                    "release": {
                        "package_names": ["org.mozilla.firefox"],
                        "google_play_track": "production",
                        "service_account": "firefox-production@iam.gserviceaccount.com",
                        "google_credentials_file": "/firefox.p12",
                        "certificate_alias": "release",
                    }
                }
            }],
            "taskcluster_scope_prefixes": ["project:releng:googleplay:"]
        })

    def generate_focus_config(self):
        work_dir = self.work_dir
        keystore_path = self.keystore_manager.keystore_path
        return self.write_config({
            "work_dir": work_dir,
            "verbose": True,

            "jarsigner_key_store": keystore_path,
            "products": [{
                "product_names": ["focus"],
                "update_google_play_strings": True,
                "digest_algorithm": "SHA1",
                "skip_check_ordered_version_codes": True,
                "skip_checks_fennec": True,
                "map_channels_to_apps": False,
                "single_app_config": {
                    "package_names": ["org.mozilla.focus", "org.mozilla.klar"],
                    "service_account": "focus@iam.gserviceaccount.com",
                    "google_credentials_file": "/focus.p12",
                    "certificate_alias": "focus",
                }
            }],
            "taskcluster_scope_prefixes": ["project:releng:googleplay:"]
        })

    def generate_fenix_config(self):
        work_dir = self.work_dir
        keystore_path = self.keystore_manager.keystore_path
        return self.write_config({
            "work_dir": work_dir,
            "verbose": True,

            "jarsigner_key_store": keystore_path,
            "products": [{
                "product_names": ["fenix"],
                "update_google_play_strings": False,
                "digest_algorithm": "SHA1",
                "skip_check_multiple_locales": True,
                "skip_check_same_locales": True,
                "skip_checks_fennec": True,
                "map_channels_to_apps": True,
                "apps": {
                    "nightly": {
                        "package_names": ["org.mozilla.fenix.nightly"],
                        "google_play_track": "beta",
                        "service_account": "fenix-nightly@iam.gserviceaccount.com",
                        "google_credentials_file": "/fenix-nightly.p12",
                        "certificate_alias": "fenix-nightly",
                    },
                    "beta": {
                        "package_names": ["org.mozilla.fenix.beta"],
                        "google_play_track": "production",
                        "service_account": "fenix-beta@iam.gserviceaccount.com",
                        "google_credentials_file": "/fenix-beta.p12",
                        "certificate_alias": "fenix-beta",
                    },
                    "release": {
                        "package_names": ["org.mozilla.fenix"],
                        "google_play_track": "production",
                        "service_account": "fenix-production@iam.gserviceaccount.com",
                        "google_credentials_file": "/fenix-production.p12",
                        "certificate_alias": "fenix-production",
                    }
                }
            }],
            "taskcluster_scope_prefixes": ["project:releng:googleplay:"]
        })


@unittest.mock.patch('pushapkscript.script.open', new=mock_open)
@unittest.mock.patch('pushapkscript.googleplay.open', new=mock_open)
class MainTest(unittest.TestCase):

    def setUp(self):
        self.test_temp_dir_fp = tempfile.TemporaryDirectory()
        self.test_temp_dir = self.test_temp_dir_fp.name
        self.keystore_manager = KeystoreManager(self.test_temp_dir, project_data_dir)

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

    def write_task_file(self, task):
        task_file = os.path.join(self.config_generator.work_dir, 'task.json')
        with open(task_file, 'w') as f:
            json.dump(task, f)

    @unittest.mock.patch('pushapkscript.googleplay.push_apk')
    def test_main_fennec_style(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task('aurora'))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate('nightly')
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='firefox-aurora@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/firefox-nightly.p12'),
            track='beta',
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
    def test_main_focus_style(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task('focus', 'production'))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate('focus')
        main(config_path=self.config_generator.generate_focus_config())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='focus@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/focus.p12'),
            track='production',
            expected_package_names=['org.mozilla.focus', 'org.mozilla.klar'],
            skip_check_package_names=False,
            rollout_percentage=None,
            google_play_strings=unittest.mock.ANY,
            commit=False,
            contact_google_play=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=True,
            skip_check_same_locales=False,
            skip_checks_fennec=True,
        )
        _, args = push_apk.call_args
        assert isinstance(args['google_play_strings'], NoGooglePlayStrings)

    @unittest.mock.patch('pushapkscript.googleplay.push_apk')
    def test_main_fenix_style(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task('fenix', 'nightly'))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate('fenix-nightly')
        main(config_path=self.config_generator.generate_fenix_config())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='fenix-nightly@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/fenix-nightly.p12'),
            track='beta',
            expected_package_names=['org.mozilla.fenix.nightly'],
            skip_check_package_names=False,
            rollout_percentage=None,
            google_play_strings=unittest.mock.ANY,
            commit=False,
            contact_google_play=True,
            skip_check_multiple_locales=True,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=True,
            skip_checks_fennec=True,
        )
        _, args = push_apk.call_args
        assert isinstance(args['google_play_strings'], NoGooglePlayStrings)


    @unittest.mock.patch('pushapkscript.googleplay.push_apk')
    def test_main_downloads_verifies_signature_and_gives_the_right_config_to_mozapkpublisher(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task('aurora'))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate('nightly')
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='firefox-aurora@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/firefox-nightly.p12'),
            track='beta',
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
        task_generator = TaskGenerator(rollout_percentage=25)
        self.write_task_file(task_generator.generate_task('aurora'))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate('nightly')
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='firefox-aurora@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/firefox-nightly.p12'),
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

        self.write_task_file(task_generator.generate_task('aurora'))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate('nightly')
        self._copy_single_file_to_test_temp_dir(
            task_id=task_generator.google_play_strings_task_id,
            origin_file_name='google_play_strings.json',
            destination_path='public/google_play_strings.json',
        )
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile(
                    '{}/work/cot/{}/public/build/target.apk'.format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            service_account='firefox-aurora@iam.gserviceaccount.com',
            google_play_credentials_file=MockFile('/firefox-nightly.p12'),
            track='beta',
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
