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

            "schema_files": {
                "submit-locale": "balrogscript/data/balrog_submit-locale_schema.json",
                "submit-toplevel": "balrogscript/data/balrog_submit-toplevel_schema.json",
                "schedule": "balrogscript/data/balrog_schedule_schema.json",
            },
            "dummy": False,
            "api_root": "BALROG_API_ROOT",
            "taskcluster_scope_prefix": "project:releng:balrog:",
            "server_config": {
                "nightly": {
                    "api_root": "BALROG_API_ROOT",
                    "auth0_domain": "AUTH0_DOMAIN",
                    "auth0_client_id": "AUTH0_CLIENT_ID",
                    "auth0_client_secret": "AUTH0_CLIENT_SECRET",
                    "auth0_audience": "AUTH0_AUDIENCE",
                    "allowed_channels": ["nightly"]
                },
                "release": {
                    "api_root": "BALROG_API_ROOT",
                    "auth0_domain": "AUTH0_DOMAIN",
                    "auth0_client_id": "AUTH0_CLIENT_ID",
                    "auth0_client_secret": "AUTH0_CLIENT_SECRET",
                    "auth0_audience": "AUTH0_AUDIENCE",
                    "allowed_channels": ["release", "release-localtest", "release-cdntest"]
                },
                "dep": {
                    "api_root": "BALROG_API_ROOT",
                    "auth0_domain": "AUTH0_DOMAIN",
                    "auth0_client_id": "AUTH0_CLIENT_ID",
                    "auth0_client_secret": "AUTH0_CLIENT_SECRET",
                    "auth0_audience": "AUTH0_AUDIENCE",
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
