import os
import unittest

from scriptworker.client import validate_task_schema
from scriptworker.context import Context
from scriptworker.exceptions import TaskVerificationError

from pushapkscript.task import extract_android_product_from_scopes

from pushapkscript.test.helpers.task_generator import TaskGenerator


class TaskTest(unittest.TestCase):
    def setUp(self):
        self.context = Context()
        self.context.config = {
            'schema_file': os.path.join(os.getcwd(), 'pushapkscript', 'data', 'pushapk_task_schema.json'),
        }

    def test_validate_task(self):
        self.context.task = TaskGenerator().generate_json()
        validate_task_schema(self.context)

    # TODO Add real life release task
    def test_validate_real_life_tasks(self):
        beta_task = {
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
        }

        self.context.task = beta_task
        validate_task_schema(self.context)

    def test_extract_supported_android_products(self):
        data = ({
            'prefix': 'project:releng:googleplay:',
            'task': {'scopes': ['project:releng:googleplay:aurora']},
            'expected': 'aurora',
        }, {
            'prefix': 'project:releng:googleplay:',
            'task': {'scopes': ['project:releng:googleplay:beta']},
            'expected': 'beta',
        }, {
            'prefix': 'project:releng:googleplay:',
            'task': {'scopes': ['project:releng:googleplay:release']},
            'expected': 'release',
        }, {
            'prefix': 'project:mobile:focus:googleplay:product:',
            'task': {'scopes': ['project:mobile:focus:googleplay:product:focus']},
            'expected': 'focus',
        })

        for item in data:
            self.context.task = item['task']
            self.context.config = {
                'taskcluster_scope_prefix': item['prefix'],
            }
            self.assertEqual(extract_android_product_from_scopes(self.context), item['expected'])

    def test_extract_android_product_from_scopes_fails_when_too_many_products_are_given(self):
        self.context.task = {
            'scopes': ['project:releng:googleplay:beta', 'project:releng:googleplay:release']
        }
        self.context.config = {
            'taskcluster_scope_prefix': 'project:releng:googleplay:',
        }
        with self.assertRaises(TaskVerificationError):
            extract_android_product_from_scopes(self.context)
