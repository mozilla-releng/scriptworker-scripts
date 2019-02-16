import copy
import json
import logging
import os
import pytest
import subprocess
import shutil
import zipfile

from mardor.cli import do_verify
from scriptworker.utils import makedirs
from signingscript.sign import sign_file_with_autograph
from signingscript.utils import SigningServer

from signingscript.script import async_main
from signingscript.test import context
from signingscript.test.integration import skip_when_no_autograph_server


assert context  # silence flake8


log = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


DEFAULT_SERVER_CONFIG = {
    'project:releng:signing:cert:dep-signing': [
        [
            'http://localhost:5500',
            'alice',
            'abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn',
            ['autograph_mar384'],
            'autograph'
        ],
        [
            'http://localhost:5500',
            'bob',
            '1234567890abcdefghijklmnopqrstuvwxyz1234567890abcd',
            ['autograph_focus'],
            'autograph'
        ],
        [
            'http://localhost:5500',
            'alice',
            'abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn',
            ['autograph_hash_only_mar384'],
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
    "taskcluster_scope_prefixes": ["project:releng:signing:"],
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


def _copy_files_to_work_dir(file_name, context):
    original_file_path = os.path.join(TEST_DATA_DIR, file_name)
    copied_file_folder = os.path.join(context.config['work_dir'], 'cot', 'upstream-task-id1')
    makedirs(copied_file_folder)
    shutil.copy(original_file_path, copied_file_folder)


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
@skip_when_no_autograph_server
async def test_integration_autograph_mar_sign_file(context, tmpdir):
    file_names = ['partial1.mar', 'partial2.mar']
    for file_name in file_names:
        _copy_files_to_work_dir(file_name, context)

    context.config['signing_server_config'] = _write_server_config(tmpdir)
    context.task = _craft_task(file_names, signing_format='autograph_mar384')

    await async_main(context)

    mar_pub_key_path = os.path.join(TEST_DATA_DIR, 'autograph_mar.pub')
    signed_paths = [os.path.join(context.config['artifact_dir'], file_name) for file_name in file_names]
    for signed_path in signed_paths:
        assert do_verify(signed_path, keyfiles=[mar_pub_key_path]), "Mar signature doesn't match expected key"


@pytest.mark.asyncio
@skip_when_no_autograph_server
async def test_integration_autograph_mar_sign_hash(context, tmpdir, mocker):
    file_names = ['partial1.mar', 'partial2.mar']
    for file_name in file_names:
        _copy_files_to_work_dir(file_name, context)

    mocker.patch('signingscript.sign.verify_mar_signature', new=lambda *args: None)
    context.config['signing_server_config'] = _write_server_config(tmpdir)
    context.task = _craft_task(file_names, signing_format='autograph_hash_only_mar384')

    await async_main(context)

    mar_pub_key_path = os.path.join(TEST_DATA_DIR, 'autograph_mar.pub')
    signed_paths = [os.path.join(context.config['artifact_dir'], file_name) for file_name in file_names]
    for signed_path in signed_paths:
        assert do_verify(signed_path, keyfiles=[mar_pub_key_path]), "Mar signature doesn't match expected key"


def _get_java_path(tool_name):
    if os.environ.get('JAVA_HOME'):
        return os.path.join(os.environ['JAVA_HOME'], 'bin', tool_name)
    return tool_name


def _instantiate_keystore(keystore_path, certificate_path, certificate_alias):
    keystore_password = '12345678'
    cmd = [
        _get_java_path('keytool'), '-import', '-noprompt',
        '-keystore', keystore_path, '-storepass', keystore_password,
        '-file', certificate_path, '-alias', certificate_alias
    ]
    log.info("running {}".format(cmd))
    subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )


def _verify_apk_signature(keystore_path, apk_path, certificate_alias):
    cmd = [
        _get_java_path('jarsigner'), '-verify', '-strict', '-verbose',
        '-keystore', keystore_path,
        apk_path,
        certificate_alias
    ]
    log.info("running {}".format(cmd))
    command = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )
    return command.returncode == 0


def _extract_compress_type_per_filename(path):
    with zipfile.ZipFile(path) as zip:
        return {
            zip_info.filename: zip_info.compress_type
            for zip_info in zip.infolist()
        }


@pytest.mark.asyncio
@skip_when_no_autograph_server
async def test_integration_autograph_focus(context, tmpdir):
    file_name = 'app.apk'
    original_file_path = os.path.join(TEST_DATA_DIR, file_name)
    copied_file_folder = os.path.join(context.config['work_dir'], 'cot', 'upstream-task-id1')
    makedirs(copied_file_folder)
    shutil.copy(original_file_path, copied_file_folder)

    zip_infos_before_signature = _extract_compress_type_per_filename(os.path.join(copied_file_folder, file_name))

    context.config['signing_server_config'] = _write_server_config(tmpdir)
    context.task = _craft_task([file_name], signing_format='autograph_focus')

    keystore_path = os.path.join(tmpdir, 'keystore')
    certificate_path = os.path.join(TEST_DATA_DIR, 'autograph_apk.pub')
    certificate_alias = 'autograph_focus'
    _instantiate_keystore(keystore_path, certificate_path, certificate_alias)

    await async_main(context)

    signed_path = os.path.join(tmpdir, 'artifact', file_name)
    assert _verify_apk_signature(keystore_path, signed_path, certificate_alias)

    zip_infos_after_signature = _extract_compress_type_per_filename(signed_path)
    for signature_file in ('META-INF/SIGNATURE.RSA', 'META-INF/SIGNATURE.SF', 'META-INF/MANIFEST.MF'):
        del zip_infos_after_signature[signature_file]

    # We want to make sure compression type hasn't changed after the signature
    # https://github.com/mozilla-services/autograph/issues/164


    assert zip_infos_before_signature == zip_infos_after_signature

def _extract_apk_signature_algorithm(apk_path):
    cmd = [
        _get_java_path('jarsigner'), '-verify', '-verbose',
        apk_path
    ]
    log.info("running {}".format(cmd))
    command = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
    )

    assert command.returncode == 0

    algorithm_line = [line for line in command.stdout.split('\n') if 'Signature algorithm:' in line][0]
    algorithm = algorithm_line.strip().split(' ')[2]
    return algorithm.rstrip(',')


# TODO change fennec algorithm to just RSA alone, then add verification of digest algorithm
@pytest.mark.asyncio
@skip_when_no_autograph_server
@pytest.mark.parametrize('format,expected_algorithm', ((
    'autograph_apk_fennec_sha1', 'SHA1withSHA1withRSA',
), (
    'autograph_apk_fennec', 'SHA256withSHA256withRSA',
)))
async def test_integration_autograph_custom_digest_algorithm(context, tmpdir, format, expected_algorithm):
    file_name = 'app.apk'
    original_file_path = os.path.join(TEST_DATA_DIR, file_name)
    shutil.copy(original_file_path, tmpdir)
    apk_path = os.path.join(tmpdir, file_name)

    context.signing_servers = {'project:releng:signing:cert:dep-signing': [SigningServer(
        *["http://localhost:5500", "bob", "1234567890abcdefghijklmnopqrstuvwxyz1234567890abcd", [format], "autograph"]
    )]}
    context.task = _craft_task([file_name], signing_format=format)

    await sign_file_with_autograph(context, apk_path, format)
    assert _extract_apk_signature_algorithm(apk_path) == expected_algorithm
