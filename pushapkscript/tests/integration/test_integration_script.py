import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import pytest

import pushapkscript
from pushapkscript.script import main

from ..helpers.mock_file import MockFile, mock_open
from ..helpers.task_generator import TaskGenerator

this_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.dirname(pushapkscript.__file__)
project_data_dir = os.path.join(project_dir, "data")
test_data_dir = os.path.join(this_dir, "..", "data")


class KeystoreManager(object):
    def __init__(self, temp_dir):
        self.keystore_path = os.path.join(temp_dir, "keystore")

    def add_certificate(self, certificate_alias):
        subprocess.run(
            [
                "keytool",
                "-import",
                "-noprompt",
                # JDK 9 changes default type to PKCS12, which causes "jarsigner -verify" to fail
                "-storetype",
                "jks",
                "-keystore",
                self.keystore_path,
                "-storepass",
                "12345678",
                "-file",
                os.path.join(project_data_dir, "android-nightly.cer"),
                "-alias",
                certificate_alias,
            ]
        )


class ConfigFileGenerator(object):
    def __init__(self, test_data_dir, keystore_manager):
        self.test_data_dir = test_data_dir
        self.keystore_manager = keystore_manager
        self.config_file = os.path.join(self.test_data_dir, "config.json")

        self.work_dir = os.path.join(test_data_dir, "work")
        os.mkdir(self.work_dir)

    def write_config(self, config):
        with open(self.config_file, "w") as f:
            json.dump(config, f)
        return self.config_file

    def generate_fennec_config(self):
        work_dir = self.work_dir
        keystore_path = self.keystore_manager.keystore_path
        return self.write_config(
            {
                "work_dir": work_dir,
                "verbose": True,
                "jarsigner_key_store": keystore_path,
                "products": [
                    {
                        "product_names": ["aurora", "beta", "release"],
                        "digest_algorithm": "SHA1",
                        "override_channel_model": "choose_google_app_with_scope",
                        "apps": {
                            "aurora": {
                                "package_names": ["org.mozilla.fennec_aurora"],
                                "default_track": "beta",
                                "credentials_file": "/firefox-nightly.json",
                                "certificate_alias": "nightly",
                            },
                            "beta": {
                                "package_names": ["org.mozilla.firefox_beta"],
                                "default_track": "production",
                                "credentials_file": "/firefox.json",
                                "certificate_alias": "release",
                            },
                            "release": {
                                "package_names": ["org.mozilla.firefox"],
                                "default_track": "production",
                                "credentials_file": "/firefox.json",
                                "certificate_alias": "release",
                            },
                        },
                    }
                ],
                "taskcluster_scope_prefixes": ["project:releng:googleplay:"],
            }
        )

    def generate_focus_config(self):
        work_dir = self.work_dir
        keystore_path = self.keystore_manager.keystore_path
        return self.write_config(
            {
                "work_dir": work_dir,
                "verbose": True,
                "jarsigner_key_store": keystore_path,
                "products": [
                    {
                        "product_names": ["focus"],
                        "digest_algorithm": "SHA1",
                        "skip_check_ordered_version_codes": True,
                        "skip_checks_fennec": True,
                        "override_channel_model": "single_google_app",
                        "app": {
                            "package_names": ["org.mozilla.focus", "org.mozilla.klar"],
                            "credentials_file": "/focus.json",
                            "certificate_alias": "focus",
                        },
                    }
                ],
                "taskcluster_scope_prefixes": ["project:releng:googleplay:"],
            }
        )

    def generate_fenix_config(self):
        work_dir = self.work_dir
        keystore_path = self.keystore_manager.keystore_path
        return self.write_config(
            {
                "work_dir": work_dir,
                "verbose": True,
                "jarsigner_key_store": keystore_path,
                "products": [
                    {
                        "product_names": ["fenix"],
                        "digest_algorithm": "SHA1",
                        "skip_check_multiple_locales": True,
                        "skip_check_same_locales": True,
                        "skip_checks_fennec": True,
                        "apps": {
                            "nightly": {
                                "package_names": ["org.mozilla.fenix.nightly"],
                                "certificate_alias": "fenix-nightly",
                                "google": {
                                    "default_track": "beta",
                                    "credentials_file": "/fenix-nightly.json",
                                },
                            },
                            "beta": {
                                "package_names": ["org.mozilla.fenix.beta"],
                                "certificate_alias": "fenix-beta",
                                "google": {
                                    "default_track": "production",
                                    "credentials_file": "/fenix-beta.json",
                                },
                            },
                            "release": {
                                "package_names": ["org.mozilla.fenix"],
                                "certificate_alias": "fenix-production",
                                "google": {
                                    "default_track": "production",
                                    "credentials_file": "/fenix-production.json",
                                },
                                "samsung": {
                                    "service_account_id": "123",
                                    "access_token": "456",
                                },
                            },
                        },
                    }
                ],
                "taskcluster_scope_prefixes": ["project:releng:googleplay:"],
            }
        )


@unittest.mock.patch("pushapkscript.script.open", new=mock_open)
@unittest.mock.patch("pushapkscript.publish.open", new=mock_open)
class MainTest(unittest.TestCase):
    def setUp(self):
        self.test_temp_dir_fp = tempfile.TemporaryDirectory()
        self.test_temp_dir = self.test_temp_dir_fp.name
        self.keystore_manager = KeystoreManager(self.test_temp_dir)

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
            self._copy_single_file_to_test_temp_dir(task_id, origin_file_name="target-{}.apk".format(task_id), destination_path="public/build/target.apk")

    def _copy_single_file_to_test_temp_dir(self, task_id, origin_file_name, destination_path):
        original_path = os.path.join(test_data_dir, origin_file_name)
        target_path = os.path.abspath(os.path.join(self.test_temp_dir, "work", "cot", task_id, destination_path))
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir)
        shutil.copy(original_path, target_path)

    def write_task_file(self, task):
        task_file = os.path.join(self.config_generator.work_dir, "task.json")
        with open(task_file, "w") as f:
            json.dump(task, f)

    @unittest.mock.patch("pushapkscript.publish.push_apk")
    def test_main_fennec_style(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task("aurora"))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate("nightly")
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            secret="/firefox-nightly.json",
            track="beta",
            expected_package_names=["org.mozilla.fennec_aurora"],
            store="google",
            rollout_percentage=None,
            dry_run=True,
            contact_server=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
            sgs_service_account_id=None,
            sgs_access_token=None,
            submit=False,
        )

    @unittest.mock.patch("pushapkscript.publish.push_apk")
    def test_main_focus_style(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task("focus", "production"))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate("focus")
        main(config_path=self.config_generator.generate_focus_config())

        push_apk.assert_called_with(
            apks=[
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            secret="/focus.json",
            track="production",
            expected_package_names=["org.mozilla.focus", "org.mozilla.klar"],
            store="google",
            rollout_percentage=None,
            dry_run=True,
            contact_server=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=True,
            skip_check_same_locales=False,
            skip_checks_fennec=True,
            sgs_service_account_id=None,
            sgs_access_token=None,
            submit=False,
        )

    @unittest.mock.patch("pushapkscript.publish.push_apk")
    def test_main_fenix_style(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task("fenix", "nightly"))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate("fenix-nightly")
        main(config_path=self.config_generator.generate_fenix_config())

        push_apk.assert_called_with(
            apks=[
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            secret="/fenix-nightly.json",
            track="beta",
            expected_package_names=["org.mozilla.fenix.nightly"],
            store="google",
            rollout_percentage=None,
            dry_run=True,
            contact_server=True,
            skip_check_multiple_locales=True,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=True,
            skip_checks_fennec=True,
            sgs_service_account_id=None,
            sgs_access_token=None,
            submit=False,
        )

    @unittest.mock.patch("pushapkscript.publish.push_apk")
    def test_main_downloads_verifies_signature_and_gives_the_right_config_to_mozapkpublisher(self, push_apk):
        task_generator = TaskGenerator()
        self.write_task_file(task_generator.generate_task("aurora"))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate("nightly")
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            secret="/firefox-nightly.json",
            track="beta",
            expected_package_names=["org.mozilla.fennec_aurora"],
            store="google",
            rollout_percentage=None,
            dry_run=True,
            contact_server=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
            sgs_service_account_id=None,
            sgs_access_token=None,
            submit=False,
        )

    @unittest.mock.patch("pushapkscript.publish.push_apk")
    def test_main_allows_rollout_percentage(self, push_apk):
        task_generator = TaskGenerator(rollout_percentage=25)
        self.write_task_file(task_generator.generate_task("aurora"))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate("nightly")
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            secret="/firefox-nightly.json",
            track="beta",
            expected_package_names=["org.mozilla.fennec_aurora"],
            store="google",
            rollout_percentage=25,
            dry_run=True,
            contact_server=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
            sgs_service_account_id=None,
            sgs_access_token=None,
            submit=False,
        )

    @unittest.mock.patch("pushapkscript.publish.push_apk")
    def test_main_allows_commit_transaction(self, push_apk):
        task_generator = TaskGenerator(should_commit_transaction=True)

        self.write_task_file(task_generator.generate_task("aurora"))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate("nightly")
        main(config_path=self.config_generator.generate_fennec_config())

        push_apk.assert_called_with(
            apks=[
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            secret="/firefox-nightly.json",
            track="beta",
            expected_package_names=["org.mozilla.fennec_aurora"],
            store="google",
            rollout_percentage=None,
            dry_run=False,
            contact_server=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
            sgs_service_account_id=None,
            sgs_access_token=None,
            submit=False,
        )

    @unittest.mock.patch("pushapkscript.publish.push_apk")
    def test_main_with_samsung_store(self, push_apk):
        task_generator = TaskGenerator(should_commit_transaction=True, store="samsung")

        self.write_task_file(task_generator.generate_task("fenix", channel="release"))

        self._copy_all_apks_to_test_temp_dir(task_generator)
        self.keystore_manager.add_certificate("nightly")
        main(config_path=self.config_generator.generate_fenix_config())

        push_apk.assert_called_with(
            apks=[
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.arm_task_id)),
                MockFile("{}/work/cot/{}/public/build/target.apk".format(self.test_temp_dir, task_generator.x86_task_id)),
            ],
            secret=None,
            track=None,
            expected_package_names=["org.mozilla.fenix"],
            store="samsung",
            rollout_percentage=None,
            dry_run=False,
            contact_server=True,
            skip_check_multiple_locales=True,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=True,
            skip_checks_fennec=True,
            sgs_service_account_id="123",
            sgs_access_token="456",
            submit=False,
        )
