import aiohttp
import asyncio
import copy
import json
import os
import pytest
import subprocess
import shutil
import tempfile
import zipfile

from mardor.cli import do_verify
from scriptworker.utils import makedirs, download_file

from signingscript.script import async_main
from signingscript.test import context
from signingscript.test.integration import skip_when_no_network


assert context  # silence flake8


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


DEFAULT_SERVER_CONFIG = {
    'project:releng:signing:cert:dep-signing': [
        [
            'https://autograph-hsm.dev.mozaws.net',
            'alice',
            'fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu',
            ['autograph_mar384'],
            'autograph'
        ],
        [
            'https://autograph-hsm.dev.mozaws.net',
            'bob',
            '9vh6bhlc10y63ow2k4zke7k0c3l9hpr8mo96p92jmbfqngs9e7d',
            ['autograph_apk'],
            'autograph'
        ],
    ]
}


DEFAULT_CONFIG = {
    "work_dir": "work_dir",
    "artifact_dir": "artifact_dir",
    "schema_file": os.path.join(DATA_DIR, 'signing_task_schema.json'),
    "signtool": "signtool",
    "ssl_cert": os.path.join(DATA_DIR, 'host.cert'),
    "taskcluster_scope_prefix": "project:releng:signing:",
    "token_duration_seconds": 1200,
    "verbose": True,
    "dmg": "dmg",
    "hfsplus": "hfsplus",
    "zipalign": "zipalign"
}


DEFAULT_TASK = {
  "created": "2016-05-04T23:15:17.908Z",
  "deadline": "2016-05-05T00:15:17.908Z",
  "dependencies": ["upstream-task-id1"],
  "expires": "2017-05-05T00:15:17.908Z",
  "extra": {},
  "metadata": {
    "description": "Markdown description of **what** this task does",
    "name": "Example Task",
    "owner": "name@example.com",
    "source": "https://tools.taskcluster.net/task-creator/"
  },
  "payload": {
    "upstreamArtifacts": [{
      "taskId": "upstream-task-id1",
      "taskType": "build",
      "paths": [],      # Configured by test
      "formats": []     # Configured by test
    }],
    "maxRunTime": 600
  },
  "priority": "normal",
  "provisionerId": "test-dummy-provisioner",
  "requires": "all-completed",
  "retries": 0,
  "routes": [],
  "schedulerId": "-",
  "scopes": [
    "project:releng:signing:cert:dep-signing",
    "project:releng:signing:autograph:dep-signing",
    # Format added by test
  ],
  "tags": {},
  "taskGroupId": "CRzxWtujTYa2hOs20evVCA",
  "workerType": "dummy-worker-aki"
}


async def _download_file(url, abs_filename, chunk_size=128):
    parent_dir = os.path.dirname(abs_filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            makedirs(parent_dir)
            with open(abs_filename, "wb") as fd:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    fd.write(chunk)


async def _download_files(urls, work_dir):
    urls_per_on_disk_path = {
        os.path.join(work_dir, 'cot/upstream-task-id1/', os.path.basename(url)): url
        for url in urls
    }
    download_tasks = [_download_file(url, on_disk_path) for on_disk_path, url in urls_per_on_disk_path.items()]
    print('Downloading original files...')
    await asyncio.gather(*download_tasks)
    print('Downloaded original files: {}'.format(urls))
    return urls_per_on_disk_path.keys()


def _write_server_config(tmpdir):
    server_config_path = os.path.join(tmpdir, 'server_config.json')
    with open(server_config_path, mode='w') as f:
        json.dump(DEFAULT_SERVER_CONFIG, f)

    return server_config_path


def _craft_task(file_names, signing_format):
    task = copy.deepcopy(DEFAULT_TASK)
    task['payload']['upstreamArtifacts'][0]['paths'] = file_names
    task['payload']['upstreamArtifacts'][0]['formats'] = [signing_format]
    task['scopes'].append('project:releng:signing:format:{}'.format(signing_format))

    return task


@pytest.mark.asyncio
@skip_when_no_network
async def test_integration_autograph_mar(context, tmpdir):
    urls_to_download = (
        'https://archive.mozilla.org/pub/firefox/nightly/2017/10/2017-10-02-22-02-04-mozilla-central/firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002220204.partial.mar',
        'https://archive.mozilla.org/pub/firefox/nightly/2017/10/2017-10-02-10-01-34-mozilla-central/firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002100134.partial.mar',
    )
    file_names = [os.path.basename(url) for url in urls_to_download]

    await _download_files(urls_to_download, context.config['work_dir'])

    context.config['signing_server_config'] = _write_server_config(tmpdir)
    context.task = _craft_task(file_names, signing_format='autograph_mar384')

    print('Running async_main...')
    await async_main(context)
    print('async_main completed')

    mar_pub_key_path = os.path.join(TEST_DATA_DIR, 'autograph_mar_dev_key.pub')
    signed_paths = [os.path.join(context.config['artifact_dir'], file_name) for file_name in file_names]
    for signed_path in signed_paths:
        assert do_verify(signed_path, keyfiles=[mar_pub_key_path]), "Signature doesn't match MAR_DEV_PUBLIC_KEY's"


def _strip_apk_signature(files):
    for file_ in files:
        temp_zip_file_path = '{}.tmp'.format(file_)
        with zipfile.ZipFile(file_, 'r') as original_zip:
            with zipfile.ZipFile(temp_zip_file_path, 'w') as temp_zip_file:
                for item in original_zip.infolist():
                    buffer = original_zip.read(item.filename)
                    if not item.filename.startswith('META-INF/'):
                        temp_zip_file.writestr(item, buffer)

            shutil.move(temp_zip_file_path, file_)


def _instanciate_keystore(keystore_path, certificate_path, certificate_alias):
    keystore_password = '12345678'
    subprocess.run([
        'keytool', '-import', '-noprompt',
        '-keystore', keystore_path, '-storepass', keystore_password,
        '-file', certificate_path, '-alias', certificate_alias
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)


def _verify_apk_signature(keystore_path, apk_path, certificate_alias):
    command = subprocess.run([
        'jarsigner', '-verify', '-strict', '-verbose',
        '-keystore', keystore_path,
        apk_path,
        certificate_alias
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return command.returncode == 0


@pytest.mark.asyncio
@skip_when_no_network
async def test_integration_autograph_apk(context, tmpdir):
    urls_to_download = (
        'https://queue.taskcluster.net/v1/task/UlL8a2zUTdqWjVFeBLIR0g/runs/0/artifacts/public/app-nightly-x86-release-signed-aligned.apk',
        'https://queue.taskcluster.net/v1/task/UlL8a2zUTdqWjVFeBLIR0g/runs/0/artifacts/public/app-nightly-arm-release-signed-aligned.apk',
    )
    file_names = [os.path.basename(url) for url in urls_to_download]

    downloaded_files = await _download_files(urls_to_download, context.config['work_dir'])
    _strip_apk_signature(downloaded_files)

    context.config['signing_server_config'] = _write_server_config(tmpdir)
    context.task = _craft_task(file_names, signing_format='autograph_apk')

    keystore_path = os.path.join(tmpdir, 'keystore')
    certificate_path = os.path.join(TEST_DATA_DIR, 'autograph_apk_dev_key.pub')
    certificate_alias = 'autograph_apk_dev_key'
    _instanciate_keystore(keystore_path, certificate_path, certificate_alias)

    print('Running async_main...')
    await async_main(context)
    print('async_main completed')

    signed_paths = [os.path.join(tmpdir, 'artifact', file_name) for file_name in file_names]
    for signed_path in signed_paths:
        assert _verify_apk_signature(keystore_path, signed_path, certificate_alias)
