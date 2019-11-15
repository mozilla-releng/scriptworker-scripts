# -*- coding: utf-8 -*-

import logging
import mock
import pytest
import os
import sys

import balrogscript.script as bscript
from balrogscript.test import (nightly_manifest, config, nightly_config,
                               release_manifest, release_config)
from balrogscript.task import (get_task, validate_task_schema, get_task_server)
from balrogscript.script import setup_logging, main, setup_config

from balrogscript.submitter.cli import (
    NightlySubmitterV4,
    ReleaseCreatorV9,
    ReleasePusher,
    ReleaseScheduler,
    ReleaseSubmitterV9,
    ReleaseStateUpdater,
)  # noqa: E402

logging.basicConfig()

assert nightly_config  # silence pyflakes
assert release_config  # silence pyflakes
assert config  # silence pyflakes
assert nightly_manifest  # silence pyflakes
assert release_manifest  # silence pyflakes

BASE_DIR = os.path.dirname(__file__)


# get_task {{{1
def test_get_task_payload(nightly_config):
    upstream = get_task(nightly_config)['payload']['upstreamArtifacts']
    assert upstream[0]['paths'][0] == 'public/manifest.json'


# create_locale_submitter {{{1
def test_create_locale_submitter_nightly_style(config, nightly_manifest):
    auth0_secrets = None
    submitter, release = bscript.create_locale_submitter(
        nightly_manifest[0], '', auth0_secrets, config)
    assert isinstance(submitter, NightlySubmitterV4)

    nightly_manifest[0].pop("partialInfo", None)
    submitter, release = bscript.create_locale_submitter(
        nightly_manifest[0], '', auth0_secrets, config)
    assert isinstance(submitter, NightlySubmitterV4)


def test_create_locale_submitter_release_style(config, release_manifest):
    auth0_secrets = None

    submitter, release = bscript.create_locale_submitter(
        release_manifest[0], '', auth0_secrets, config)
    assert isinstance(submitter, ReleaseSubmitterV9)

    release_manifest[0].pop("partialInfo", None)
    submitter, release = bscript.create_locale_submitter(
        release_manifest[0], '', auth0_secrets, config)
    assert isinstance(submitter, ReleaseSubmitterV9)

    release_manifest[0].pop("tc_release", None)
    with pytest.raises(RuntimeError):
        submitter, release = bscript.create_locale_submitter(
            release_manifest[0], '', auth0_secrets, config)


def test_create_locale_submitter_nightly_metadata(config, nightly_manifest):
    auth0_secrets = None
    submitter, release = bscript.create_locale_submitter(
        nightly_manifest[0], '', auth0_secrets, config)

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


def test_create_locale_submitter_nightly_creates_valid_submitter(config, nightly_manifest):
    auth0_secrets = None
    submitter, release = bscript.create_locale_submitter(
        nightly_manifest[0], '', auth0_secrets, config)
    lambda: submitter.run(**release)


# submit_locale {{{1
def test_submit_locale(config, nightly_config, nightly_manifest, mocker):
    auth0_secrets = None
    _, release = bscript.create_locale_submitter(nightly_manifest[0], '', auth0_secrets, config)

    def fake_submitter(**kwargs):
        assert kwargs == release

    task = get_task(nightly_config)
    m = mock.MagicMock()
    m.run = fake_submitter
    mocker.patch.object(bscript, "create_locale_submitter", return_value=(m, release))
    bscript.submit_locale(task, config, auth0_secrets)


# schedule {{{1
def test_create_scheduler(config):
    assert isinstance(
        bscript.create_scheduler(api_root=config['api_root'], auth0_secrets=None),
        ReleaseScheduler
    )


def test_schedule(config, mocker):
    auth0_secrets = None

    task = {
        'payload': {
            'product': 'foo',
            'version': '99.bottles',
            'build_number': 7,
            'publish_rules': [1, 2],
            'release_eta': None,
        }
    }
    expected = ["Foo", '99.bottles', 7, [1, 2], None]
    real = []

    def fake_scheduler(*args):
        # Don't assert here; retry() will retry
        real.extend(args)

    def fake_retry(c):
        return c()

    m = mock.MagicMock()
    m.run = fake_scheduler
    mocker.patch.object(bscript, "create_scheduler", return_value=m)

    bscript.schedule(task, config, auth0_secrets)
    assert real == expected


# submit_toplevel {{{1
def test_create_creator(config):
    assert isinstance(
        bscript.create_creator(api_root=config['api_root'], auth0_secrets=None),
        ReleaseCreatorV9
    )


def test_create_pusher(config):
    assert isinstance(
        bscript.create_pusher(api_root=config['api_root'], auth0_secrets=None),
        ReleasePusher
    )


@pytest.mark.parametrize("task,creator_expected,pusher_expected", ((
    {
        'payload': {
            'app_version': '60.0',
            'product': 'widget',
            'version': '60',
            'build_number': 8,
            'channel_names': ['x', 'y'],
            'archive_domain': 'archive',
            'download_domain': 'download',
            'platforms': ['foo', 'bar'],
            'require_mirrors': False,
            'rules_to_update': [1],
        }
    },
    {
        'appVersion': '60.0',
        'productName': 'Widget',
        'version': '60',
        'buildNumber': 8,
        'updateChannels': ['x', 'y'],
        'ftpServer': 'archive',
        'bouncerServer': 'download',
        'enUSPlatforms': ['foo', 'bar'],
        'hashFunction': 'sha512',
        'partialUpdates': {},
        'requiresMirrors': False,
        'updateLine': None,
    },
    {
        'productName': 'Widget',
        'version': '60',
        'build_number': 8,
        'rule_ids': [1],
    },
), (
    {
        'payload': {
            'app_version': '60.0',
            'product': 'widget',
            'version': '60',
            'build_number': 8,
            'channel_names': ['x', 'y'],
            'archive_domain': 'archive',
            'download_domain': 'download',
            'partial_versions': '40build2, 50build4',
            'platforms': ['foo', 'bar'],
            'require_mirrors': True,
            'rules_to_update': [1],
        }
    },
    {
        'appVersion': '60.0',
        'productName': 'Widget',
        'version': '60',
        'buildNumber': 8,
        'updateChannels': ['x', 'y'],
        'ftpServer': 'archive',
        'bouncerServer': 'download',
        'enUSPlatforms': ['foo', 'bar'],
        'hashFunction': 'sha512',
        'partialUpdates': {
            '40': {'buildNumber': '2'},
            '50': {'buildNumber': '4'},
        },
        'requiresMirrors': True,
        'updateLine': None,
    },
    {
        'productName': 'Widget',
        'version': '60',
        'build_number': 8,
        'rule_ids': [1],
    },
), (
    {
        'payload': {
            'app_version': '60.0',
            'product': 'widget',
            'version': '60',
            'build_number': 8,
            'channel_names': ['x', 'y'],
            'archive_domain': 'archive',
            'download_domain': 'download',
            'partial_versions': '40build2, 50build4',
            'platforms': ['foo', 'bar'],
            'require_mirrors': True,
            'rules_to_update': [1],
            'update_line': {'': {
                'for': {},
                'fields': {'detailsURL': 'https://some.text/details', 'type': 'minor'},
            }},
        }
    },
    {
        'appVersion': '60.0',
        'productName': 'Widget',
        'version': '60',
        'buildNumber': 8,
        'updateChannels': ['x', 'y'],
        'ftpServer': 'archive',
        'bouncerServer': 'download',
        'enUSPlatforms': ['foo', 'bar'],
        'hashFunction': 'sha512',
        'partialUpdates': {
            '40': {'buildNumber': '2'},
            '50': {'buildNumber': '4'},
        },
        'requiresMirrors': True,
        'updateLine': {
            'for': {},
            'fields': {'detailsURL': 'https://some.text/details', 'type': 'minor'},
        },
    },
    {
        'productName': 'Widget',
        'version': '60',
        'build_number': 8,
        'rule_ids': [1],
    },
)))
def test_submit_toplevel(task, creator_expected, pusher_expected, nightly_config, mocker):
    auth0_secrets = None
    results = []

    def fake(**kwargs):
        results.append(kwargs)

    m = mock.MagicMock()
    m.run = fake

    mocker.patch.object(bscript, "create_creator", return_value=m)
    mocker.patch.object(bscript, "create_pusher", return_value=m)
    bscript.submit_toplevel(task, nightly_config, auth0_secrets)
    assert results[0] == creator_expected
    assert results[1] == pusher_expected


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
    validate_task_schema(config, test_taskdef, 'submit-locale')


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
        validate_task_schema(config, defn, 'submit-locale')


# get_task_server {{{1
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
    assert bscript.log.level == logging.NOTSET


# load_config {{{1
def test_load_config():
    config_path = os.path.join(BASE_DIR, 'data/hardcoded_config.json')
    assert bscript.load_config(config_path)['verbose']
    with pytest.raises(SystemExit):
        bscript.load_config(os.path.join(BASE_DIR, "nonexistent.path"))


def test_create_state_updater(config):
    assert isinstance(
        bscript.create_state_updater(api_root=config['api_root']),
        ReleaseStateUpdater
    )


def test_set_readonly(config, mocker):
    task = {
        'payload': {
            'product': 'foo',
            'version': '42.0.24',
            'build_number': 1,
        }
    }

    expected = ['Foo', '42.0.24', 1]
    real = []

    def fake_run(*args):
        real.extend(args)

    m = mock.MagicMock()
    m.run = fake_run
    mocker.patch.object(bscript, "create_state_updater", return_value=m)

    bscript.set_readonly(task, config, None)
    assert real == expected


# setup_config {{{1
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


# main {{{1
@pytest.mark.parametrize("action", ('submit-locale', 'submit-toplevel', 'schedule'))
def test_main_submit_locale(action, mocker):

    def fake_get_action(*args):
        return action

    def fake_get_manifest(config, upstream_artifacts):
        return []

    config_path = os.path.join(BASE_DIR, 'data/hardcoded_config.json')

    mocker.patch.object(bscript, "validate_task_schema")
    mocker.patch.object(bscript, "get_task_action", return_value=action)
    mocker.patch.object(bscript, "submit_toplevel")
    mocker.patch.object(bscript, "submit_locale")
    mocker.patch.object(bscript, "schedule")

    main(config_path=config_path)
