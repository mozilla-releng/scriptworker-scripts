# -*- coding: utf-8 -*-

import balrogscript.balrogscript as balrogscript
import json
import logging
import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "../tools/lib/python"
))

from balrog.submitter.cli import NightlySubmitterV4, ReleaseSubmitterV4

logging.basicConfig()

# constants, helpers, and fixtures {{{1
NIGHTLY_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "nightly_manifest.json")
RELEASE_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "release_manifest.json")
NIGHTLY_TASK_PATH = os.path.join(os.path.dirname(__file__), "data", "nightly_task.json")
RELEASE_TASK_PATH = os.path.join(os.path.dirname(__file__), "data", "release_task.json")


@pytest.fixture(scope='function')
def nightly_manifest():
    with open(NIGHTLY_MANIFEST_PATH, "r") as fh:
        return json.load(fh)


@pytest.fixture(scope='function')
def release_manifest():
    with open(RELEASE_MANIFEST_PATH, "r") as fh:
        return json.load(fh)


@pytest.yield_fixture(scope='function')
def config():
    with tempfile.TemporaryDirectory as t:
        tmpdir = t.name
        yield {
            "work_dir": os.path.join(tmpdir, "work_dir"),
            "artifact_dir": os.path.join(tmpdir, "artifact_dir"),
            "schema_file": "balrogscript/data/balrog_task_schema.json",
            "dummy": False,
            "api_root": "BALROG_API_ROOT",
            "balrog_username": "BALROG_USERNAME",
            "balrog_password": "BALROG_PASSWORD",
            "s3_bucket": "S3_BUCKET",
            "aws_key_id": "AWS_ACCESS_KEY_ID",
            "aws_key_secret": "AWS_SECRET_ACCESS_KEY",
            "disable_certs": False,
            "disable_s3": True,
            "verbose": True
        }


# tests {{{1
def test_get_hash():
    test_content = "wow. much text. very hash ☺️"
    test_md5 = "d0bfbdf85fac3ccd5a9d9a458bf39ab3"
    assert balrogscript.get_hash(test_content) == test_md5


def test_get_hash_fail():
    test_content = "sometimes i swordfight with pocky ⚔⚔"
    test_md5 = "thisisnot⚔arealhash"
    assert balrogscript.get_hash(test_content) != test_md5


def test_get_hash_sha512():
    test_content = "wow. much text. مرحبا"
    test_sha = "e643580dcb98a8d9a7b95890d12f793baf5ef09a79695003" \
               "fbcaf3b54c1c96cb56aeccbd360209c5cd234117dea1cc88aa60b2a250dd4858ee1d6847cb7a8c7e"
    assert balrogscript.get_hash(test_content, hash_type="sha512") == test_sha


def test_possible_names():
    initial = "/Users/tester/file.exe"
    names = balrogscript.possible_names(initial, 2)
    exp = ["/Users/tester/file.exe", "/Users/tester/file-1.exe", "/Users/tester/file-2.exe"]
    assert set(names) == set(exp)


def test_possible_names_neg():
    initial = "file.exe"
    names = balrogscript.possible_names(initial, -1)
    exp = ["file.exe"]
    assert set(names) == set(exp)


def test_load_task_payload():
    url, cert = balrogscript.load_task('test_nightly.json')
    assert url == 'https://queue.taskcluster.net/v1/task/e2q3BKuhRxqtcB6FVCbKfg/artifacts/public/env'


def test_load_task_cert():
    url, cert = balrogscript.load_task('test_nightly.json')
    assert 'nightly' in cert


def test_verify_copy_to_s3_returns_tc_url(config):
    url = balrogscript.verify_copy_to_s3(config, "return this url", "")
    assert url == "return this url"


def test_create_submitter_nightly_style(config):
    # Execute task with S3 disabled for these tests
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, config)
    assert isinstance(submitter, NightlySubmitterV4)


def test_create_submitter_nightly_metadata(config):
    # Execute task with S3 disabled for these tests
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, config)

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


def test_create_submitter_nightly_creates_valid_submitter(config):
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, config)
    lambda: submitter.run(**release)


def test_create_submitter_release_submission_type(config):
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, config)
    assert isinstance(submitter,ReleaseSubmitterV4)


def test_create_submitter_release_metadata(config):
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

    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, config)

    assert release == exp

def test_create_submitter_release_creates_valid_submitter(config):
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, config)
    lambda: submitter.run(**release)


def test_verify_task_schema(config):
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
    balrogscript.verify_task_schema(config, test_taskdef)


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
def test_verify_task_schema_missing_cert(config, defn):
    with pytest.raises(SystemExit):
        balrogscript.verify_task_schema(config, defn)
