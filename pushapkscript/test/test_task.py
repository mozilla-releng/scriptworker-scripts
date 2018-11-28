import os
import pytest

from scriptworker.client import validate_task_schema
from scriptworker.context import Context
from scriptworker.exceptions import TaskVerificationError

from pushapkscript.task import extract_android_product_from_scopes

from pushapkscript.test.helpers.task_generator import TaskGenerator


@pytest.fixture
def context():
    context_ = Context()
    context_.config = {
        'schema_file': os.path.join(os.getcwd(), 'pushapkscript', 'data', 'pushapk_task_schema.json'),
    }
    return context_


def test_validate_task(context):
    context.task = TaskGenerator().generate_json()
    validate_task_schema(context)


# TODO Add real life release task
@pytest.mark.parametrize('task', (
    {
        "provisionerId": "scriptworker-prov-v1",
        "workerType": "pushapk-v1",
        "schedulerId": "gecko-level-3",
        "taskGroupId": "dG0aircORb-VaKCK8X-grw",
        "dependencies": [
            "TjtRhOazQJ6_lNYYDMjAGA",
            "R-GBCWrDQiW7UP1nPALXMg",
            "TmzjU_G6ReepFBGOCATlpw"
        ],
        "requires": "all-completed",
        "routes": [
                    "tc-treeherder.v2.mozilla-beta.35a1b06fe7863e118ce831d9056ad20501eec606.0",
                    "tc-treeherder-stage.v2.mozilla-beta.35a1b06fe7863e118ce831d9056ad20501eec606.0"
        ],
        "priority": "normal",
        "retries": 5,
        "created": "2017-04-11T03:47:20.427Z",
        "deadline": "2017-04-16T03:47:20.427Z",
        "expires": "2018-04-11T03:47:20.427Z",
        "scopes": [
                    "project:releng:googleplay:beta"
        ],
        "payload": {
            "upstreamArtifacts": [{
                "paths": [
                    "public/build/target.apk"
                ],
                "taskId": "TjtRhOazQJ6_lNYYDMjAGA",
                "taskType": "signing"
            }, {
                "paths": [
                    "public/build/target.apk"
                ],
                "taskId": "TmzjU_G6ReepFBGOCATlpw",
                "taskType": "signing"
            }
            ],
            "google_play_track": "production",
            "commit": True
        },
        "metadata": {
            "owner": "r@m.c",
            "source": "https://hg.mozilla.org/releases/mozilla-beta/file/35a1b06fe7863e118ce831d9056ad20501eec606/taskcluster/ci/push-apk",
            "description": "Publishes APK onto Google Play Store \
    ([Treeherder push](https://treeherder.mozilla.org/#/jobs?repo=mozilla-beta&revision=35a1b06fe7863e118ce831d9056ad20501eec606))",
            "name": "push-apk/opt"
        },
        "tags": {
            "createdForUser": "r@m.c"
        },
        "extra": {
            "treeherderEnv": [
                "production",
                "staging"
            ],
            "treeherder": {
                "jobKind": "other",
                "groupSymbol": "pub",
                "collection": {
                    "opt": True
                },
                "machine": {
                    "platform": "Android"
                },
                "groupName": "APK publishing",
                "tier": 2,
                "symbol": "gp"
            }
        }
    },
))
def test_validate_real_life_tasks(context, task):
    context.task = task
    validate_task_schema(context)


@pytest.mark.parametrize('prefix, task, expected', ((
    'project:releng:googleplay:',
    {'scopes': ['project:releng:googleplay:aurora']},
    'aurora',
), (
    'project:releng:googleplay:',
    {'scopes': ['project:releng:googleplay:beta']},
    'beta',
), (
    'project:releng:googleplay:',
    {'scopes': ['project:releng:googleplay:release']},
    'release',
), (
    'project:mobile:focus:googleplay:product:',
    {'scopes': ['project:mobile:focus:googleplay:product:focus']},
    'focus',
), (
    'project:mobile:reference-browser:googleplay:product:',
    {'scopes': ['project:mobile:reference-browser:googleplay:product:reference-browser:dep']},
    'reference-browser',
)))
def test_extract_supported_android_products(context, prefix, task, expected):
    context.task = task
    context.config = {
        'taskcluster_scope_prefix': prefix,
    }
    assert extract_android_product_from_scopes(context) == expected


def test_extract_android_product_from_scopes_fails_when_too_many_products_are_given(context):
    context.task = {
        'scopes': ['project:releng:googleplay:beta', 'project:releng:googleplay:release']
    }
    context.config = {
        'taskcluster_scope_prefix': 'project:releng:googleplay:',
    }
    with pytest.raises(TaskVerificationError):
        extract_android_product_from_scopes(context)
