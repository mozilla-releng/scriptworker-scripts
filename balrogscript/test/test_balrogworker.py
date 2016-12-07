# -*- coding: utf-8 -*-

import balrogscript.balrogscript as balrogscript
import unittest
from nose.tools import raises, with_setup
import logging
import json
import pytest
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "../tools/lib/python"
))

from balrog.submitter.cli import NightlySubmitterV4, ReleaseSubmitterV4

logging.basicConfig()

nightly_manifest = [
    {
        "tc_nightly": True,
        "completeInfo": [{
            "url": "http://bucketlister-delivery.stage.mozaws.net/pub/mobile/nightly/latest-date-android-api-15/fennec-52.0a1.multi.android.arm.apk",
            "size": "33256909",
            "hash": "7934e31946358f0b541e9b877e0ab70bce58580e1bf015fc63f70e1c8b4c8c835e38a3ef92f790c78ba7d71cd4b930987f2a99e8c58cf33e7ae118d3b1c42485"
        }],
        "platform": "android-api-15",
        "buildid": "20161107171219",
        "appName": "Fennec",
        "branch": "date",
        "appVersion": "52.0a1",
        "locale": "en-US",
        "hashType": "sha512",
        "extVersion": "52.0a1",
        "url_replacements": "..."
    }
]
release_manifest = [
    {
        "ACCEPTED_MAR_CHANNEL_IDS": "firefox-mozilla-release",
        "appName": "Firefox",
        "branch": "mozilla-release",
        "detached_signatures": {
            "gpg": "firefox-48.0b10-48.0.en-US.linux-x86_64.partial.mar.asc"
        },
        "from_buildid": "20160721144529",
        "from_hash": "cc9f91ab4e8f79a2431ead22faad28cd8bec0fda58c7578b050db6c5d7d3c37c907f4cf72ce78934bbfdf5f39373de46b622c2db571890e31bfa0cac751964d7",
        "from_mar": "http://download.mozilla.org/?product=firefox-48.0b10-complete&os=linux64&lang=en-US",
        "from_size": 55915191,
        "hash": "56452b46ba9f00c9bf74f7c403ec4d96e0a996f2dedce81b8d6782f5e9133f25854c5b8d66e16afd3c19b7215c2c6bdbf21361258936a2746717c6661987ef5e",
        "locale": "en-US",
        "mar": "firefox-48.0b10-48.0.en-US.linux-x86_64.partial.mar",
        "platform": "linux64",
        "previousBuildNumber": 1,
        "previousVersion": "48.0b10",
        "repo": "https://hg.mozilla.org/releases/mozilla-release",
        "revision": "a55778f9cd5a98d05fb50a9a295ef8da379e41d0",
        "size": 10026844,
        "toBuildNumber": 1,
        "toVersion": "48.0",
        "to_buildid": "20160725093659",
        "to_hash": "139cb84767eddceb2f8bc0b98b3bc5c1e41d52c208edaa3d429281229f3ed53b241bd78b1666eadf206f2e7b4d578c89d08942ec40184870b144a7fa6b3a7fb8",
        "to_mar": "https://queue.taskcluster.net/v1/task/JeR2raZMRU6aeB86I-kCYw/artifacts/public/build/firefox-48.0.en-US.linux-x86_64.complete.mar",
        "to_size": 55889576,
        "version": "48.0"
    }
]


class BalrogworkerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nightly = {
            'dependencies': ['blah'],
            'scopes': ['blah'],
            'payload': {
                'parent_task_artifacts_url': 'https://queue.taskcluster.net/v1/task/e2q3BKuhRxqtcB6FVCbKfg/artifacts/public/env',
                'signing_cert': 'nightly',
                'upstreamArtifacts': [{
                    "paths": ["foo"],
                    "taskId": "bar",
                    "taskType": "baz",
                }],
            }
        }

        release = {
            'dependencies': ['blah'],
            'scopes': ['blah'],
            'payload': {
                'parent_task_artifacts_url': 'https://public-artifacts.taskcluster.net/RrV9Kn17RbCcnkl4ttDuIA/1/public/env',
                'signing_cert': 'release',
                'upstreamArtifacts': [{
                    "paths": ["foo"],
                    "taskId": "bar",
                    "taskType": "baz",
                }],
            }
        }
        with open('test_nightly.json', 'w') as f:
            json.dump(nightly, f)
        with open('test_release.json', 'w') as f:
            json.dump(release, f)

    @classmethod
    def tearDownClass(cls):
        os.remove('test_nightly.json')
        os.remove('test_release.json')

    def test_get_hash(self):
        test_content = "wow. much text. very hash ☺️"
        test_md5 = "d0bfbdf85fac3ccd5a9d9a458bf39ab3"
        assert balrogscript.get_hash(test_content) == test_md5

    def test_get_hash_fail(self):
        test_content = "sometimes i swordfight with pocky ⚔⚔"
        test_md5 = "thisisnot⚔arealhash"
        assert balrogscript.get_hash(test_content) != test_md5

    def test_get_hash_sha512(self):
        test_content = "wow. much text. مرحبا"
        test_sha = "e643580dcb98a8d9a7b95890d12f793baf5ef09a79695003" \
                   "fbcaf3b54c1c96cb56aeccbd360209c5cd234117dea1cc88aa60b2a250dd4858ee1d6847cb7a8c7e"
        assert balrogscript.get_hash(test_content, hash_type="sha512") == test_sha

    def test_possible_names(self):
        initial = "/Users/tester/file.exe"
        names = balrogscript.possible_names(initial, 2)
        exp = ["/Users/tester/file.exe", "/Users/tester/file-1.exe", "/Users/tester/file-2.exe"]
        assert set(names) == set(exp)

    def test_possible_names_neg(self):
        initial = "file.exe"
        names = balrogscript.possible_names(initial, -1)
        exp = ["file.exe"]
        assert set(names) == set(exp)


    def test_load_task_payload(self):
        url, cert = balrogscript.load_task('test_nightly.json')
        assert url == 'https://queue.taskcluster.net/v1/task/e2q3BKuhRxqtcB6FVCbKfg/artifacts/public/env'

    def test_load_task_cert(self):
        url, cert = balrogscript.load_task('test_nightly.json')
        assert 'nightly' in cert

    def get_nightly_args(self):
        return ["--taskdef", "test_nightly.json",
                "--balrog-api-root", "TEST_API_ROOT",
                "--balrog-username", "fake balrog user",
                "--balrog-password", "very good passwrod",
                "--s3-bucket", "bucket walrus",
                "--aws-access-key-id", "cocoa butter",
                "--aws-secret-access-key", "shhhhhhhhhhh",
                "--disable-s3"]

    def get_nightly_args_processed(self):
        return {
            "taskdef": "test_nightly.json",
            "api_root": "TEST_API_ROOT",
            "balrog_username": "fake balrog user",
            "balrog_password": "very good passwrod",
            "s3_bucket": "bucket walrus",
            "aws_key_id": "cocoa butter",
            "aws_key_secret": "shhhhhhhhhhh",
            "disable_s3": True,
            "disable_certs": False,
            "dummy": False,
            "loglevel": 20,  # corresponds to default value of logging.INFO
            "parent_url": "https://queue.taskcluster.net/v1/task/e2q3BKuhRxqtcB6FVCbKfg/artifacts/public/env",
            "signing_cert": "nightly"
        }

    def get_args_as_environ(self):
        return {
            "BALROG_API_ROOT": "TEST_API_ROOT",
            "BALROG_USERNAME": "fake balrog user",
            "BALROG_PASSWORD": "very good passwrod",
            "S3_BUCKET": "bucket walrus",
            "AWS_ACCESS_KEY_ID": "cocoa butter",
            "AWS_SECRET_ACCESS_KEY": "shhhhhhhhhhh",
        }

    def test_verify_args(self):
        args = vars(balrogscript.verify_args(self.get_nightly_args()))
        exp = self.get_nightly_args_processed()
        for key in args:
            if key == 'signing_cert':
                continue
            assert exp[key] == args[key]

    def test_args_provides_correct_key_path(self):
        args = balrogscript.verify_args(self.get_nightly_args())
        assert os.path.isfile(args.signing_cert)


    def test_verify_args_from_environ(self):
        os.environ.update(self.get_args_as_environ())
        expected = self.get_nightly_args_processed()
        for key, value in vars(balrogscript.verify_args(["--taskdef", "test_nightly.json", "--disable-s3"])).iteritems():
            if key == 'signing_cert':
                continue
            assert expected[key] == value

    def create_args_dict(self):
        os.environ.update(self.get_args_as_environ())
        return balrogscript.verify_args(["--taskdef", "test_nightly.json", "--disable-s3"])

    def test_verify_copy_to_s3_returns_tc_url(self):
        args = self.create_args_dict()

        url = balrogscript.verify_copy_to_s3(args, "return this url", "")
        assert url == "return this url"

    def test_create_submitter_nightly_style(self):
        # Execute task with S3 disabled for these tests
        args = balrogscript.verify_args(["--taskdef", "test_nightly.json", "--disable-s3"])
        balrog_auth = (None, None)
        submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, args)
        assert isinstance(submitter, NightlySubmitterV4)

    def test_create_submitter_nightly_metadata(self):
        # Execute task with S3 disabled for these tests
        args = balrogscript.verify_args(["--taskdef", "test_nightly.json", "--disable-s3"])
        balrog_auth = (None, None)
        submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, args)

        exp = {
            'platform': "android-api-15",
            'buildID': "20161107171219",
            'productName': "Fennec",
            'branch': "date",
            'appVersion': "52.0a1",
            'locale': "en-US",
            'hashFunction': "sha512",
            'extVersion': "52.0a1",
            'completeInfo': [{
                "url": "http://bucketlister-delivery.stage.mozaws.net/pub/mobile/nightly/latest-date-android-api-15/fennec-52.0a1.multi.android.arm.apk",
                "size": "33256909",
                "hash": "7934e31946358f0b541e9b877e0ab70bce58580e1bf015fc63f70e1c8b4c8c835e38a3ef92f790c78ba7d71cd4b930987f2a99e8c58cf33e7ae118d3b1c42485"
            }]
        }
        assert exp == release

    def test_create_submitter_nightly_creates_valid_submitter(self):
        args = balrogscript.verify_args(["--taskdef", "test_nightly.json", "--disable-s3"])
        balrog_auth = (None, None)
        submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, args)
        lambda: submitter.run(**release)


    def test_create_submitter_release_submission_type(self):
        args = balrogscript.verify_args(["--taskdef", "test_release.json", "--disable-s3"])
        balrog_auth = (None, None)
        submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, args)
        assert isinstance(submitter,ReleaseSubmitterV4)

    def test_create_submitter_release_metadata(self):
        exp = {
            'partialInfo': [{
                'previousVersion': '48.0b10',
                'hash': '56452b46ba9f00c9bf74f7c403ec4d96e0a996f2dedce81b8d6782f5e9133f25854c5b8d66e16afd3c19b7215c2c6bdbf21361258936a2746717c6661987ef5e',
                'previousBuildNumber': 1, 'size': 10026844}], 'build_number': 1, 'extVersion': '48.0',
            'buildID': '20160725093659', 'appVersion': '48.0', 'productName': 'Firefox', 'platform': 'linux64',
            'version': '48.0', 'hashFunction': 'sha512', 'locale': 'en-US',
            'completeInfo': [{
                'hash': '139cb84767eddceb2f8bc0b98b3bc5c1e41d52c208edaa3d429281229f3ed53b241bd78b1666eadf206f2e7b4d578c89d08942ec40184870b144a7fa6b3a7fb8',
                'size': 55889576}]}

        args = balrogscript.verify_args(["--taskdef", "test_release.json", "--disable-s3"])
        balrog_auth = (None, None)
        submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, args)

        assert release == exp

    def test_create_submitter_release_creates_valid_submitter(self):
        args = balrogscript.verify_args(["--taskdef", "test_release.json", "--disable-s3"])
        balrog_auth = (None, None)
        submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, args)
        lambda: submitter.run(**release)


def test_verify_task_schema():
    test_taskdef = {
        'scopes': ['blah'],
        'dependencies': ['blah'],
        'payload': {
            'parent_task_artifacts_url': "blah",
            'signing_cert': 'nightly',
            'upstreamArtifacts': [{
                "paths": ["foo"],
                "taskId": "bar",
                "taskType": "baz",
            }],
        }
    }
    balrogscript.verify_task_schema(test_taskdef)


@pytest.mark.parametrize("defn", ({
    'dependencies': ['blah'],
    'payload': {
        'parent_task_artifacts_url': "blah",
        'signing_cert': 'nightly',
        'upstreamArtifacts': [{
            "paths": ["foo"],
            "taskId": "bar",
            "taskType": "baz",
        }],
    }
}, {
    'scopes': ['blah'],
    'payload': {
        'parent_task_artifacts_url': "blah",
        'signing_cert': 'nightly',
        'upstreamArtifacts': [{
            "paths": ["foo"],
            "taskId": "bar",
            "taskType": "baz",
        }],
    }
}, {
    'dependencies': ['blah'],
    'scopes': ['blah'],
    'payload': {
        'parent_task_artifacts_url': "blah",
        'signing_cert': 'nightly',
    }
}))
def test_verify_task_schema_missing_cert(defn):
    with pytest.raises(SystemExit):
        balrogscript.verify_task_schema(defn)
