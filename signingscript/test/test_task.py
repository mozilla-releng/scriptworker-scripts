import unittest
import asynctest

from signingscript.script import get_default_config
from signingscript.task import validate_task_schema, download_files
from signingscript.exceptions import DownloadError

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.test.helpers.task_generator import TaskGenerator


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


class TaskTestAsync(asynctest.TestCase):
    def setUp(self):
        self.context = Context()
        self.context.config = get_default_config()
        self.context.task = TaskGenerator().generate_json()

    @asynctest.patch('signingscript.utils.download_file')
    async def test_download_files_returns_absolute_paths(self, _):
        files = await download_files(self.context)
        path_prefix = '{}/public/build/fennec-46.0a2.en-US.android'.format(self.context.config['work_dir'])
        self.assertEqual(files, {
            'armv7_v15': '{}-arm.apk'.format(path_prefix),
            'x86': '{}-i386.apk'.format(path_prefix),
        })

    @asynctest.patch('signingscript.utils.download_file')
    async def test_download_files_raises_download_error(self, download_file):
        def download_error(*args):
            raise DownloadError("Not 200!")

        download_file.side_effect = download_error
        with self.assertRaises(DownloadError):
            await download_files(self.context)
