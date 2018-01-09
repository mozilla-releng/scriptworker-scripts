import json
import os
import pytest
import shutil
import tempfile


# constants, helpers, and fixtures {{{1
NIGHTLY_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "nightly_manifest.json")
NIGHTLY_TASK_PATH = os.path.join(os.path.dirname(__file__), "data", "nightly_task.json")
RELEASE_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "release_manifest.json")
RELEASE_TASK_PATH = os.path.join(os.path.dirname(__file__), "data", "release_task.json")


@pytest.fixture(scope='function')
def nightly_manifest():
    with open(NIGHTLY_MANIFEST_PATH, "r") as fh:
        return json.load(fh)


@pytest.fixture(scope='function')
def release_manifest():
    with open(RELEASE_MANIFEST_PATH, "r") as fh:
        return json.load(fh)


@pytest.yield_fixture(scope='function')
def config():
    tmpdir = tempfile.mkdtemp()
    try:
        yield {
            "work_dir": os.path.join(tmpdir, "work_dir"),
            "artifact_dir": os.path.join(tmpdir, "artifact_dir"),

            "schema_file": "balrogscript/data/balrog_task_schema.json",
            "dummy": False,
            "api_root": "BALROG_API_ROOT",
            "server_config": {
                "nightly": {
                    "api_root": "BALROG_API_ROOT",
                    "balrog_username": "BALROG_USERNAME",
                    "balrog_password": "BALROG_PASSWORD",
                    "allowed_channels": ["nightly"]
                },
                "release": {
                    "api_root": "BALROG_API_ROOT",
                    "balrog_username": "BALROG_USERNAME",
                    "balrog_password": "BALROG_PASSWORD",
                    "allowed_channels": ["release", "release-localtest", "release-cdntest"]
                },
                "dep": {
                    "api_root": "BALROG_API_ROOT",
                    "balrog_username": "BALROG_USERNAME",
                    "balrog_password": "BALROG_PASSWORD",
                    "allowed_channels": ["nightly", "release", "beta", "etc"]
                },

            },
            "disable_certs": False,
            "verbose": True
        }
    finally:
        shutil.rmtree(tmpdir)


@pytest.yield_fixture(scope='function')
def nightly_config(config):
    os.makedirs(os.path.join(config['work_dir'], "cot", "upstream-task-id", "public"))
    shutil.copyfile(
        NIGHTLY_MANIFEST_PATH,
        os.path.join(config['work_dir'], "cot", "upstream-task-id", "public", "manifest.json")
    )
    shutil.copyfile(
        NIGHTLY_TASK_PATH,
        os.path.join(config['work_dir'], "task.json")
    )
    yield config


@pytest.yield_fixture(scope='function')
def release_config(config):
    os.makedirs(os.path.join(config['work_dir'], "cot", "upstream-task-id", "public"))
    shutil.copyfile(
        RELEASE_MANIFEST_PATH,
        os.path.join(config['work_dir'], "cot", "upstream-task-id", "public", "manifest.json")
    )
    shutil.copyfile(
        RELEASE_TASK_PATH,
        os.path.join(config['work_dir'], "task.json")
    )
    yield config
