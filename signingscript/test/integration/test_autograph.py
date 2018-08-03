import aiohttp
import asyncio
import json
import os
import pytest
import tempfile

from mardor.cli import do_verify
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


MAR_DEV_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAt/a7CnyvRF9XIc4FzoI1
W0g8B2XBs2DDPNj+P6GL7TIxjLY57hsfLKcfCZ4DDSdflgr1yDnhTgGYrUJTw6wL
zXUtnZyoYSqTjtTJqTRM3aKgFLnFYkXtBBVfOk/guOiefUbaPJNF8Fxz/qL8Eunp
ae8MtyQpolk/s1f0xic30KXLk0muWaC9lsO+YcQW67q31pfgKMhdKZT0T12252r/
NaauZtcIHFTUN0NT7seAGhu6pwvFHV+u2BBEauvU8u/7FqRiqdH+dXCLX6FFYmJz
CxCcDjQHL+XYUqWdS/xci8sbZaADAht499HNG6cRjn/6mbZPWDpuLh/boU5MpEcM
e9Ji1P3P+1Vdcezppc8Jc1IfnA1Wyz2u9qNqF30/f7emTAGHmw+79ri3WzX26zzt
gQyA11aREjdctGvht2u6mN44dNFnFF8JCz3AD9VItLcMe6OGfVv5uiSC5AbRJzGr
MORa6g6Rfz193ueqmFgNC8mnsa3e+I1UwaCfvzdJnxmrGTabaHMqF30ra3YmmqYZ
NshnjR8y4NtjFEiTGDNTy7le5sxltbqQwnehGTHQ5h98dwEBuuWfz6ZiB+WQob1t
UFmedTKy6crONPQyc+mlv5EoC5C9AhiZN0KwauOG5LDaGGmHBC7dqYYsAAKcVnk4
Quo7lAFcSz0Cx1MEcNTpWhUCAwEAAQ==
-----END PUBLIC KEY-----
"""


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
# ), (
    # (
    #     'https://queue.taskcluster.net/v1/task/UlL8a2zUTdqWjVFeBLIR0g/runs/0/artifacts/public/app-nightly-x86-release-signed-aligned.apk',
    #     'https://queue.taskcluster.net/v1/task/UlL8a2zUTdqWjVFeBLIR0g/runs/0/artifacts/public/app-nightly-arm-release-signed-aligned.apk',
    # ),
    # 'autograph_apk',
),))
async def test_integration_autograph(context, tmpdir, urls_to_download, format):
    file_names = [os.path.basename(url) for url in urls_to_download]
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
    context.task['payload']['upstreamArtifacts'][0]['paths'] = file_names
    context.task['payload']['upstreamArtifacts'][0]['formats'] = [format]
    context.task['scopes'].append('project:releng:signing:format:{}'.format(format))

    await async_main(context)

    mar_pub_key_path = os.path.join(tmpdir, 'mar_pub_key')
    with open(mar_pub_key_path, mode='w') as f:
        f.write(MAR_DEV_PUBLIC_KEY)

    # TODO same for APK
    signed_paths = [os.path.join(tmpdir, 'artifact', file_name) for file_name in file_names]
    for signed_path in signed_paths:
        assert do_verify(signed_path, keyfiles=[mar_pub_key_path]), "Signature doesn't match MAR_DEV_PUBLIC_KEY's"
