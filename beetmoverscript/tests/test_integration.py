import json
from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest

import beetmoverscript.script
from beetmoverscript.constants import BUILDHUB_ARTIFACT
from beetmoverscript.script import main
from beetmoverscript.utils import load_json, write_json

from . import get_fake_valid_config


def get_test_task(task_name):
    return load_json(f"tests/task_examples/{task_name}.json")


_CONFIG_MAP = {
    "android-components": {
        "taskcluster_scope_prefix": "project:mobile:android-components:releng:beetmover:",
        "bucket_config_key": "maven-nightly-staging",
        "bucket_name": "nightly_components",
    },
    "app-services": {
        "taskcluster_scope_prefix": "project:mozilla:app-services:releng:beetmover:",
        "bucket_config_key": "maven-production",
        "bucket_name": "appservices",
    },
    "geckoview": {"taskcluster_scope_prefix": "project:releng:beetmover:", "bucket_config_key": "maven-production", "bucket_name": "geckoview"},
    "glean": {"taskcluster_scope_prefix": "project:mozilla:glean:releng:beetmover:", "bucket_config_key": "maven-production", "bucket_name": "telemetry"},
    "firefox-nightly": {"taskcluster_scope_prefix": "project:releng:beetmover:", "bucket_config_key": "nightly", "bucket_name": "firefox"},
    "firefox-langpacks": {"taskcluster_scope_prefix": "project:releng:beetmover:", "bucket_config_key": "release", "bucket_name": "devedition"},
    "firefox-generated-screenshots": {"taskcluster_scope_prefix": "project:releng:beetmover:", "bucket_config_key": "release", "bucket_name": "firefox"},
}


def get_config(config_name):
    config = get_fake_valid_config()
    config_props = _CONFIG_MAP[config_name]
    config["taskcluster_scope_prefix"] = config_props["taskcluster_scope_prefix"]
    config["bucket_config"][config_props["bucket_config_key"]] = {
        "buckets": {config_props["bucket_name"]: "dummy"},
        "credentials": {"id": "dummy", "key": "dummy"},
        "url_prefix": "https://url.prefix",
    }
    return config


def create_dummy_artifacts_for_task(task, root_path):
    """Create artifacts to upload as specified in the given task."""
    for artifact_dict in task["payload"]["upstreamArtifacts"]:
        task_id = artifact_dict["taskId"]
        for path in artifact_dict["paths"]:
            full_path = root_path / task_id / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            create_dummy_artifact(full_path)


def create_dummy_artifact(file_path):
    if file_path.name == BUILDHUB_ARTIFACT:
        with open(file_path, "w") as f:
            write_json(file_path, {"download": {}})
    else:
        with open(file_path, "wb") as f:
            f.write(b"some data")


def get_paths_for_task(task):
    """Generates a dictionary containing the source artifact path for every destination."""
    paths = {}
    for artifact_dict in task["payload"]["artifactMap"]:
        for path, path_dict in artifact_dict["paths"].items():
            for dest in path_dict["destinations"]:
                assert dest not in paths
                paths[dest] = path

    return paths


@pytest.fixture
def boto3_client_mock(monkeypatch):
    client_mock = Mock(spec=beetmoverscript.script.boto3.client("s3"))

    def fake_generate_presigned_url(ClientMethod, Params=None, *args, **kwargs):
        return f"presigned_url+{Params['Key']}"

    client_mock.generate_presigned_url = fake_generate_presigned_url

    def fake_boto3_client_only_s3(*args, **kwargs):
        assert args[0] == "s3", "A client other than 's3' was requested"
        return client_mock

    monkeypatch.setattr(beetmoverscript.script.boto3, "client", fake_boto3_client_only_s3)

    return client_mock


@pytest.fixture
def aiohttp_session_mock(monkeypatch):
    aiohttp_mock_data = {}

    async def fake_text():
        return "response_text"

    response_mock = Mock(spec=beetmoverscript.script.aiohttp.ClientResponse)
    response_mock.text = fake_text
    response_mock.status = 200

    @asynccontextmanager
    async def fake_put(url, data=None, **kwargs):
        aiohttp_mock_data.setdefault("put", []).append({"url": url, "data": data.read(), "source": data.name})
        yield response_mock

    session_mock = Mock(spec=beetmoverscript.script.aiohttp.ClientSession)
    session_mock.put = fake_put

    @asynccontextmanager
    async def fake_ClientSession(**kwargs):
        yield session_mock

    monkeypatch.setattr(beetmoverscript.script.aiohttp, "ClientSession", fake_ClientSession)
    return aiohttp_mock_data


def prepare_scriptworker_config(path, config, task):
    work_dir = path / "work"
    work_dir.mkdir()
    config["work_dir"] = str(work_dir)

    # An artifact dir is needed with a public subdir for push-to-nightly paths
    artifact_dir = path / "artifact"
    artifact_dir.mkdir()
    (artifact_dir / "public").mkdir()
    config["artifact_dir"] = str(artifact_dir)

    config_path = path / "config.json"
    with open(config_path, "w") as config_file:
        json.dump(config, config_file)

    with open(work_dir / "task.json", "w") as task_file:
        json.dump(task, task_file)

    create_dummy_artifacts_for_task(task, work_dir / "cot")

    return config_path


@pytest.mark.parametrize(
    "config_name, task_name, expected_number_of_artifacts",
    (
        ("android-components", "android_components_nightly", 12),
        ("geckoview", "geckoview_nightly", 16),
        ("app-services", "application_services_release", 12),
        ("glean", "glean_release", 20),
        ("firefox-nightly", "firefox_desktop_nightly", 52),
        ("firefox-langpacks", "firefox_langpacks_beta", 1),
        ("firefox-generated-screenshots", "firefox_generated_screenshots_release", 7),
    ),
)
def test_main_maven_nightly_candidates(config_name, task_name, expected_number_of_artifacts, tmp_path, boto3_client_mock, aiohttp_session_mock):
    config = get_config(config_name)
    task = get_test_task(task_name)
    scriptworker_config = prepare_scriptworker_config(tmp_path, config, task)

    main(config_path=scriptworker_config)

    # Number of artifacts put matches expected
    assert len(aiohttp_session_mock["put"]) == expected_number_of_artifacts

    # Check paths
    expected_paths = get_paths_for_task(task)
    # Check that the destinations match exactly, and that they have been through signing
    expected_signed_paths = set(f"presigned_url+{dest}" for dest in expected_paths)
    assert expected_signed_paths == set(put_call["url"] for put_call in aiohttp_session_mock["put"])
    # Check that the source matches expected for every destination
    for put_call in aiohttp_session_mock["put"]:
        if not put_call["url"].endswith(".json"):
            assert put_call["data"] == b"some data"
        _, unsigned_url = put_call["url"].split("+")
        assert put_call["source"].endswith(expected_paths[unsigned_url])

