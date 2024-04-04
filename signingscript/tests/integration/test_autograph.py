import copy
import json
import logging
import os
import shutil
import subprocess
import zipfile

import aiohttp
import pytest
import cryptography.x509
from cryptography.hazmat.primitives import hashes
from conftest import skip_when_no_autograph_server
from mardor.cli import do_verify
from scriptworker.utils import makedirs

from signingscript.script import async_main
from signingscript.sign import sign_file_with_autograph
from signingscript.utils import Autograph

log = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


DEFAULT_SERVER_CONFIG = {
    "project:releng:signing:cert:dep-signing": [
        ["http://localhost:5500", "alice", "abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn", ["autograph_mar384"]],
        ["http://localhost:5500", "bob", "1234567890abcdefghijklmnopqrstuvwxyz1234567890abcd", ["autograph_focus"]],
        ["http://localhost:5500", "alice", "abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn", ["autograph_hash_only_mar384"]],
        ["http://localhost:5500", "charlie", "abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn", ["autograph_authenticode"]],
    ]
}


DEFAULT_CONFIG = {
    "work_dir": "work_dir",
    "artifact_dir": "artifact_dir",
    "schema_file": os.path.join(DATA_DIR, "signing_task_schema.json"),
    "taskcluster_scope_prefixes": ["project:releng:signing:"],
    "verbose": True,
    "dmg": "dmg",
    "hfsplus": "hfsplus",
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
        "source": "https://tools.taskcluster.net/task-creator/",
    },
    "payload": {
        "upstreamArtifacts": [{"taskId": "upstream-task-id1", "taskType": "build", "paths": [], "formats": []}],  # Configured by test  # Configured by test
        "maxRunTime": 600,
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
    "workerType": "dummy-worker-aki",
}


def _copy_files_to_work_dir(file_name, context):
    original_file_path = os.path.join(TEST_DATA_DIR, file_name)
    copied_file_folder = os.path.join(context.config["work_dir"], "cot", "upstream-task-id1")
    makedirs(copied_file_folder)
    shutil.copy(original_file_path, copied_file_folder)


def _write_server_config(tmpdir):
    server_config_path = os.path.join(tmpdir, "server_config.json")
    with open(server_config_path, mode="w") as f:
        json.dump(DEFAULT_SERVER_CONFIG, f)

    return server_config_path


def _craft_task(file_names, signing_format):
    task = copy.deepcopy(DEFAULT_TASK)
    task["payload"]["upstreamArtifacts"][0]["paths"] = file_names
    task["payload"]["upstreamArtifacts"][0]["formats"] = [signing_format]
    task["scopes"].append("project:releng:signing:format:{}".format(signing_format))

    return task


@pytest.mark.asyncio
@skip_when_no_autograph_server
async def test_integration_autograph_mar_sign_file(context, tmpdir):
    file_names = ["partial1.mar", "partial2.mar"]
    for file_name in file_names:
        _copy_files_to_work_dir(file_name, context)

    context.config["autograph_configs"] = _write_server_config(tmpdir)
    context.task = _craft_task(file_names, signing_format="autograph_mar384")

    await async_main(context)

    mar_pub_key_path = os.path.join(TEST_DATA_DIR, "autograph_mar.pub")
    signed_paths = [os.path.join(context.config["artifact_dir"], file_name) for file_name in file_names]
    for signed_path in signed_paths:
        assert do_verify(signed_path, keyfiles=[mar_pub_key_path]), "Mar signature doesn't match expected key"


@pytest.mark.asyncio
@skip_when_no_autograph_server
async def test_integration_autograph_mar_sign_hash(context, tmpdir, mocker):
    file_names = ["partial1.mar", "partial2.mar"]
    for file_name in file_names:
        _copy_files_to_work_dir(file_name, context)

    mocker.patch("signingscript.sign.verify_mar_signature", new=lambda *args: None)
    context.config["autograph_configs"] = _write_server_config(tmpdir)
    context.task = _craft_task(file_names, signing_format="autograph_hash_only_mar384")

    await async_main(context)

    mar_pub_key_path = os.path.join(TEST_DATA_DIR, "autograph_mar.pub")
    signed_paths = [os.path.join(context.config["artifact_dir"], file_name) for file_name in file_names]
    for signed_path in signed_paths:
        assert do_verify(signed_path, keyfiles=[mar_pub_key_path]), "Mar signature doesn't match expected key"


def _verify_apk_signature(apk_path, certificate, strict=True):
    cmd = ["apksigner", "verify", "--verbose", "--print-certs"]
    if strict:
        cmd.append("-Werr")
    cmd.append(apk_path)
    log.info("running {}".format(cmd))
    command = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE)

    if command.returncode != 0:
        return False

    for line in command.stdout.splitlines():
        if line.startswith("Signer #1 certificate SHA-256 digest: "):
            cert_fpr = certificate.fingerprint(hashes.SHA256()).hex()
            found_fpr = line.split(":", 1)[1].strip()
            return found_fpr == cert_fpr

    return False


def _extract_compress_type_per_filename(path):
    with zipfile.ZipFile(path) as zip:
        return {zip_info.filename: zip_info.compress_type for zip_info in zip.infolist()}


@pytest.mark.asyncio
@skip_when_no_autograph_server
async def test_integration_autograph_focus(context, tmpdir):
    file_name = "app.apk"
    original_file_path = os.path.join(TEST_DATA_DIR, file_name)
    copied_file_folder = os.path.join(context.config["work_dir"], "cot", "upstream-task-id1")
    makedirs(copied_file_folder)
    shutil.copy(original_file_path, copied_file_folder)

    zip_infos_before_signature = _extract_compress_type_per_filename(os.path.join(copied_file_folder, file_name))

    context.config["autograph_configs"] = _write_server_config(tmpdir)
    context.task = _craft_task([file_name], signing_format="autograph_focus")

    certificate_path = os.path.join(TEST_DATA_DIR, "autograph_apk.pub")
    with open(certificate_path, "rb") as f:
        certificate = cryptography.x509.load_pem_x509_certificate(f.read())

    await async_main(context)

    signed_path = os.path.join(tmpdir, "artifact", file_name)
    assert _verify_apk_signature(signed_path, certificate)

    zip_infos_after_signature = _extract_compress_type_per_filename(signed_path)
    for file in list(zip_infos_after_signature):
        if file.startswith("META-INF/"):
            del zip_infos_after_signature[file]

    # We want to make sure compression type hasn't changed after the signature
    # https://github.com/mozilla-services/autograph/issues/164

    assert zip_infos_before_signature == zip_infos_after_signature


@pytest.mark.asyncio
@skip_when_no_autograph_server
async def test_integration_autograph_authenticode(context, tmpdir):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_ca"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_ca_timestamp"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_timestamp_style"] = None
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_url"] = "https://example.com"
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            Autograph(*["http://localhost:5500", "charlie", "abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn", ["autograph_authenticode"]])
        ]
    }
    context.config["autograph_configs"] = _write_server_config(tmpdir)
    _copy_files_to_work_dir("windows.zip", context)
    context.task = _craft_task(["windows.zip"], signing_format="autograph_authenticode")

    await async_main(context)
