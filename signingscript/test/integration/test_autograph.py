import aiohttp
import asyncio
import json
import os
import pytest
import tempfile

from scriptworker.utils import makedirs, download_file

from signingscript.script import async_main
from signingscript.test import context

assert context  # silence flake8


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')


DEFAULT_SERVER_CONFIG = {
    'project:releng:signing:cert:dep-signing': [
        [
            'https://autograph-hsm.dev.mozaws.net',
            'alice',
            'fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu',
            ['autograph_mar384', 'autograph_fenix'],
            'autograph'
        ]
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


@pytest.mark.asyncio
@pytest.mark.parametrize('urls_to_download, format', ((
    (
        'https://archive.mozilla.org/pub/firefox/nightly/2017/10/2017-10-02-22-02-04-mozilla-central/firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002220204.partial.mar',
        'https://archive.mozilla.org/pub/firefox/nightly/2017/10/2017-10-02-10-01-34-mozilla-central/firefox-mozilla-central-58.0a1-linux-x86_64-en-US-20171001220301-20171002100134.partial.mar',
    ),
    'autograph_mar384',
), (
    (
        'https://queue.taskcluster.net/v1/task/UlL8a2zUTdqWjVFeBLIR0g/runs/0/artifacts/public/app-nightly-x86-release-signed-aligned.apk',
        'https://queue.taskcluster.net/v1/task/UlL8a2zUTdqWjVFeBLIR0g/runs/0/artifacts/public/app-nightly-arm-release-signed-aligned.apk',
    ),
    'autograph_fenix',
)))
async def test_autograph_signs_mar(context, tmpdir, urls_to_download, format):
    artifact_dir = os.path.join(tmpdir, 'artifact_dir')
    urls_per_on_disk_path = {
        os.path.join(context.config['work_dir'], 'cot/upstream-task-id1/', os.path.basename(url)): url
        for url in urls_to_download
    }
    download_tasks = [_download_file(url, on_disk_path) for on_disk_path, url in urls_per_on_disk_path.items()]
    await asyncio.gather(*download_tasks)

    server_config_path = os.path.join(tmpdir, 'server_config.json')
    with open(server_config_path, mode='w') as f:
        json.dump(DEFAULT_SERVER_CONFIG, f)

    context.config['signing_server_config'] = server_config_path
    context.task = DEFAULT_TASK
    context.task['payload']['upstreamArtifacts'][0]['paths'] = [
        os.path.basename(url) for url in urls_to_download
    ]
    context.task['payload']['upstreamArtifacts'][0]['formats'] = [format]
    context.task['scopes'].append('project:releng:signing:format:{}'.format(format))

    await async_main(context)

    # TODO: check mar is valid and signed with the hsm-dev
