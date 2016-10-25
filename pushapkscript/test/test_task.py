import unittest
import asynctest

from pushapkscript.script import get_default_config
from pushapkscript.task import validate_task_schema, download_files, extract_channel
from pushapkscript.exceptions import TaskVerificationError

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from pushapkscript.test.helpers.task_generator import TaskGenerator


class TaskTest(unittest.TestCase):
    def setUp(self):
        self.context = Context()
        self.context.config = get_default_config()

    def test_validate_task(self):
        self.context.task = TaskGenerator().generate_json()
        validate_task_schema(self.context)

    def test_missing_mandatory_apks_are_reported(self):
        self.context.task = TaskGenerator(
            apks={'armv7_v15': ''}  # x86 is missing, for instance
        ).generate_json()

        with self.assertRaises(ScriptWorkerTaskException):
            validate_task_schema(self.context)

    def test_no_error_is_reported_when_no_missing_apk(self):
        self.context.task = TaskGenerator(
            apks={'armv7_v15': '', 'x86': ''}
        ).generate_json()

        validate_task_schema(self.context)

    def test_extract_supported_channels(self):
        data = ({
            'task': {'scopes': ['project:releng:googleplay:aurora']},
            'expected': 'aurora'
        }, {
            'task': {'scopes': ['project:releng:googleplay:beta']},
            'expected': 'beta'
        }, {
            'task': {'scopes': ['project:releng:googleplay:release']},
            'expected': 'release'
        })

        for item in data:
            self.assertEqual(extract_channel(item['task']), item['expected'])

    def test_extract_channel_fails_when_too_many_channels_are_given(self):
        with self.assertRaises(TaskVerificationError):
            extract_channel({
                'scopes': ['project:releng:googleplay:beta', 'project:releng:googleplay:release']
            })

    def test_extract_channel_fails_when_given_unsupported_channel(self):
        with self.assertRaises(TaskVerificationError):
            extract_channel({
                'scopes': ['project:releng:googleplay:unexistingchannel']
            })


class TaskTestAsync(asynctest.TestCase):
    def setUp(self):
        self.context = Context()
        self.context.config = get_default_config()
        self.context.task = TaskGenerator().generate_json()

    @asynctest.patch('scriptworker.task.download_artifacts')
    async def test_download_files_returns_absolute_paths(self, download_artifacts):
        def convert_url_into_paths(_, file_urls):
            url_with_all_slashes = [url.replace('%2F', '/') for url in file_urls]
            file_names = [url.split('/')[-1] for url in url_with_all_slashes]
            return ['public/build/{}'.format(file_name) for file_name in file_names]

        download_artifacts.side_effect = convert_url_into_paths
        path_prefix = '{}/public/build/fennec-46.0a2.en-US.android'.format(self.context.config['work_dir'])
        files = await download_files(self.context)

        self.assertEqual(files, {
            'armv7_v15': '{}-arm.apk'.format(path_prefix),
            'x86': '{}-i386.apk'.format(path_prefix),
        })
