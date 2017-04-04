# -*- coding: utf-8 -*-

import json
import logging
import pytest
import os
import shutil
import sys
import tempfile
import balrogscript.script as balrogscript
from balrogscript.task import (get_task, validate_task_schema, get_task_server)

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "../tools/lib/python"
))
from balrog.submitter.cli import NightlySubmitterV4  # noqa: E402

logging.basicConfig()

# constants, helpers, and fixtures {{{1
NIGHTLY_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "nightly_manifest.json")
NIGHTLY_TASK_PATH = os.path.join(os.path.dirname(__file__), "data", "nightly_task.json")


@pytest.fixture(scope='function')
def nightly_manifest():
    with open(NIGHTLY_MANIFEST_PATH, "r") as fh:
        return json.load(fh)


@pytest.yield_fixture(scope='function')
def config():
    tmpdir = tempfile.mkdtemp()
    try:
        yield {
            "work_dir": os.path.join(tmpdir, "work_dir"),
            "artifact_dir": os.path.join(tmpdir, "artifact_dir"),
            "schema_file": "balrogscript/data/balrog_task_schema.json",
            "dummy": False,
            "api_root": "BALROG_API_ROOT",
            "server_config": {
                "nightly": {
                    "balrog_username": "BALROG_USERNAME",
                    "balrog_password": "BALROG_PASSWORD",
                    "allowed_channels": ["nightly"]
                },
            },
            "disable_certs": False,
            "verbose": True
        }
    finally:
        shutil.rmtree(tmpdir)


@pytest.yield_fixture(scope='function')
def nightly_config(config):
    os.makedirs(os.path.join(config['work_dir'], "upstream-task-id", "public"))
    shutil.copyfile(
        NIGHTLY_MANIFEST_PATH,
        os.path.join(config['work_dir'], "upstream-task-id", "public", "manifest.json")
    )
    shutil.copyfile(
        NIGHTLY_TASK_PATH,
        os.path.join(config['work_dir'], "task.json")
    )
    yield config


# get_task {{{1
def test_get_task_payload(nightly_config):
    upstream = get_task(nightly_config)['payload']['upstreamArtifacts']
    assert upstream[0]['paths'][0] == 'public/manifest.json'


# create_submitter {{{1
def test_create_submitter_nightly_style(config, nightly_manifest):
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, config)
    assert isinstance(submitter, NightlySubmitterV4)


def test_create_submitter_nightly_metadata(config, nightly_manifest):
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


def test_create_submitter_nightly_creates_valid_submitter(config, nightly_manifest):
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, config)
    lambda: submitter.run(**release)


# validate_task_schema {{{1
def test_validate_task_schema(config):
    test_taskdef = {
        'scopes': ['blah'],
        'dependencies': ['blah'],
        'payload': {
            'upstreamArtifacts': [{
                "paths": ["foo"],
                "taskId": "bar",
                "taskType": "baz",
            }],
        }
    }
    validate_task_schema(config, test_taskdef)


@pytest.mark.parametrize("defn", ({
    'dependencies': ['blah'],
    'payload': {
        'upstreamArtifacts': [{
            "paths": ["foo"],
            "taskId": "bar",
            "taskType": "baz",
        }],
    }
}, {
    'scopes': ['blah'],
    'payload': {
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
    }
}))
def test_verify_task_schema_missing_cert(config, defn):
    with pytest.raises(SystemExit):
        validate_task_schema(config, defn)


@pytest.mark.parametrize("defn", ({
    'dependencies': [u'blah'],
    'payload': {
        'upstreamArtifacts': [{
            'paths': ['foo'],
            'taskId': 'bar',
            'taskType': u'bazaa'
        }],
    },
    'scopes': [
        'project:releng:balrog:nightly',
    ]
}, {
    'dependencies': [u'blah'],
    'payload': {
        'upstreamArtifacts': [{
            'paths': ['foo'],
            'taskId': 'bar',
            'taskType': u'bazaa'
        }],
    },
    'scopes': [
        'project:releng:balrog:server:@#($*@#($&@',
    ]
}, {
    'dependencies': [u'blah'],
    'payload': {
        'upstreamArtifacts': [{
            'paths': ['foo'],
            'taskId': 'bar',
            'taskType': u'bazaa'
        }],
    },
    'scopes': [
        'project:releng:balrog:nightly',
        'project:releng:balrog:beta',
    ]
}, {
    'dependencies': [u'blah'],
    'payload': {
        'upstreamArtifacts': [{
            'paths': ['foo'],
            'taskId': 'bar',
            'taskType': u'bazaa'
        }],
    },
    'scopes': [
        'project:releng:balrog:server:nightly-something',
    ]
}))
def test_get_task_server(config, defn):
    with pytest.raises(ValueError):
        get_task_server(defn, config)
