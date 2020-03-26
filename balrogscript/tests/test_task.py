# -*- coding: utf-8 -*-
import pytest

from balrogscript.task import get_manifest, get_task_action, get_task_server, get_upstream_artifacts


@pytest.mark.parametrize(
    "scopes,expected,raises",
    (
        (["project:releng:balrog:server:dep", "project:releng:balrog:server:release"], None, True),
        (["project:releng:balrog:server:!!"], None, True),
        (["project:releng:balrog:server:foo", "project:releng:balrog:action:foo"], None, True),
        (["project:releng:balrog:server:dep", "project:releng:balrog:action:foo"], "dep", False),
    ),
)
def test_get_task_server(nightly_task, nightly_config, scopes, expected, raises):
    task = nightly_task
    task["scopes"] = scopes

    if raises:
        with pytest.raises(ValueError):
            get_task_server(task, nightly_config)
    else:
        assert expected == get_task_server(task, nightly_config)


@pytest.mark.parametrize("expected", ([[{"paths": ["public/manifest.json"], "taskId": "upstream-task-id", "taskType": "baz"}]]))
def test_get_upstream_artifacts(nightly_task, nightly_config, expected):
    assert get_upstream_artifacts(nightly_task) == expected


@pytest.mark.parametrize(
    "expected_manifest",
    (
        [
            [
                {
                    "tc_nightly": True,
                    "completeInfo": [
                        {
                            "url": "http://bucketlister-delivery.stage.mozaws.net/pub/mobile/nightly/latest-date-android-api-15/fennec-52.0a1.multi.android.arm.apk",  # noqa: E501
                            "size": "33256909",
                            "hash": "7934e31946358f0b541e9b877e0ab70bce58580e1bf015fc63f70e1c8b4c8c835e38a3ef92f790c78ba7d71cd4b930987f2a99e8c58cf33e7ae118d3b1c42485",  # noqa: E501
                        }
                    ],
                    "partialInfo": [
                        {
                            "hash": "adf17a9d282294befce1588d0d4b0678dffc326df28f8a6d8d379e4d79bcf3ec5469cb7f12b018897b8a4d17982bf6810dc9d3ceffd65ebb8621fdddb2ace826",  # noqa: E501
                            "url": "http://stage/pub/mobile/nightly/firefox-mozilla-central-59.0a1-linux-x86_64-is-20180105220204-20180107220443.partial.mar",
                            "size": 8286275,
                            "from_buildid": 20180105220204,
                        }
                    ],
                    "platform": "android-api-15",
                    "buildid": "20161107171219",
                    "appName": "Fennec",
                    "branch": "date",
                    "appVersion": "52.0a1",
                    "locale": "en-US",
                    "hashType": "sha512",
                    "extVersion": "52.0a1",
                    "url_replacements": "...",
                }
            ]
        ]
    ),
)
def test_nightly_get_manifest(nightly_task, nightly_config, expected_manifest):
    upstream_artifacts = get_upstream_artifacts(nightly_task)

    manifest = get_manifest(nightly_config, upstream_artifacts)
    assert manifest == expected_manifest


def test_release_get_manifest(release_task, release_config):
    upstream_artifacts = get_upstream_artifacts(release_task)

    # munge the path with a fake path
    upstream_artifacts[0]["paths"][0] += "munged_path_entry"
    with pytest.raises(SystemExit) as e:
        get_manifest(release_config, upstream_artifacts)
        assert e.type == SystemExit
        assert e.value.code == 3


@pytest.mark.parametrize(
    "task,expected,raises",
    (
        ({"scopes": ["project:releng:balrog:action:submit-locale"]}, "submit-locale", False),
        ({"scopes": ["project:releng:balrog:action:submit-toplevel"]}, "submit-toplevel", False),
        ({"scopes": ["project:releng:balrog:action:schedule"]}, "schedule", False),
        ({"scopes": ["project:releng:balrog:action:schedule", "project:releng:balrog:action:submit-locale"]}, None, True),
        ({"scopes": ["project:releng:balrog:action:illegal"]}, None, True),
        ({"scopes": []}, "submit-locale", False),
    ),
)
def test_get_task_action(task, expected, raises):
    if raises:
        with pytest.raises(ValueError):
            get_task_action(task, {"taskcluster_scope_prefix": "project:releng:balrog:"})
    else:
        assert get_task_action(task, {"taskcluster_scope_prefix": "project:releng:balrog:"}) == expected
