# -*- coding: utf-8 -*-

import logging
import mock
import pytest
import os
import sys

import balrogscript.script as balrogscript
from balrogscript.test import (nightly_manifest, config, nightly_config,
                               release_manifest, release_config)
from balrogscript.task import (get_task, validate_task_schema, get_task_server)
from balrogscript.script import setup_logging, main, setup_config

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "../tools/lib/python"
))
from balrog.submitter.cli import NightlySubmitterV4, ReleaseSubmitterV4  # noqa: E402

logging.basicConfig()

assert nightly_config  # silence pyflakes
assert release_config  # silence pyflakes
assert config  # silence pyflakes
assert nightly_manifest  # silence pyflakes
assert release_manifest  # silence pyflakes


# get_task {{{1
def test_get_task_payload(nightly_config):
    upstream = get_task(nightly_config)['payload']['upstreamArtifacts']
    assert upstream[0]['paths'][0] == 'public/manifest.json'


# create_submitter {{{1
def test_create_submitter_nightly_style(config, nightly_manifest):
    balrog_auth = (None, None)
    submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, config)
    assert isinstance(submitter, NightlySubmitterV4)

    nightly_manifest[0].pop("partialInfo", None)
    submitter, release = balrogscript.create_submitter(nightly_manifest[0], balrog_auth, config)
    assert isinstance(submitter, NightlySubmitterV4)


def test_create_submitter_release_style(config, release_manifest):
    balrog_auth = (None, None)

    submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, config)
    assert isinstance(submitter, ReleaseSubmitterV4)

    release_manifest[0].pop("partialInfo", None)
    submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, config)
    assert isinstance(submitter, ReleaseSubmitterV4)

    release_manifest[0].pop("tc_release", None)
    with pytest.raises(RuntimeError):
        submitter, release = balrogscript.create_submitter(release_manifest[0], balrog_auth, config)


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
        }],
        "partialInfo": [
            {
                "hash": "adf17a9d282294befce1588d0d4b0678dffc326df28f8a6d8d379e4d79bcf3ec5469cb7f12b018897b8a4d17982bf6810dc9d3ceffd65ebb8621fdddb2ace826",
                "url": "http://stage/pub/mobile/nightly/firefox-mozilla-central-59.0a1-linux-x86_64-is-20180105220204-20180107220443.partial.mar",
                "size": 8286275,
                "from_buildid": 20180105220204
            }
        ],
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


# setup_logging {{{1
@pytest.mark.parametrize("verbose", (
    True, False
))
def test_setup_logging(verbose):
    setup_logging(verbose=verbose)
    assert logging.getLogger().level == logging.NOTSET


def test_invalid_args():
    args = ['only-one-arg']
    with mock.patch.object(sys, 'argv', args):
        with pytest.raises(SystemExit) as e:
            setup_config(None)
            assert e.type == SystemExit
            assert e.value.code == 2

    args = ['balrogscript', 'balrogscript/test/data/hardcoded_config.json']
    with mock.patch.object(sys, 'argv', args):
        config = setup_config(None)
        assert config['artifact_dir'] == 'balrogscript/data/balrog_task_schema.json'


def test_main():
    def fake_retry(action):
        return

    def fake_get_manifest(config, upstream_artifacts):
        return []

    with pytest.raises(SystemExit) as e:
        main(name='__main__')
        assert e.type == SystemExit
        assert e.value.code == 2

    with pytest.raises(SystemExit) as e:
        main(name='__main__', config_path='balrogscript/test/data/hardcoded_config.json.json')
        assert e.type == SystemExit
        assert e.value.code == 5

    with mock.patch('util.retry.retry', new=fake_retry):
        main(name='__main__', config_path='balrogscript/test/data/hardcoded_config.json')

    with mock.patch('balrogscript.script.get_manifest', new=fake_get_manifest):
        main(name='__main__', config_path='balrogscript/test/data/hardcoded_config.json')
