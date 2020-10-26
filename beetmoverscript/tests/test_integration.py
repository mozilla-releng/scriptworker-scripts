import json
from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest

import beetmoverscript.script
from beetmoverscript.script import main

from . import get_fake_valid_config


@pytest.fixture
def config():
    config = get_fake_valid_config()
    config["taskcluster_scope_prefix"] = "project:mobile:android-components:releng:beetmover:"
    config["bucket_config"]["maven-nightly-staging"] = {"buckets": {"nightly_components": "dummy"}, "credentials": {"id": "dummy", "key": "dummy"}}
    return config


@pytest.fixture
def task():
    return {
        "dependencies": ["dependency-task-id"],
        "scopes": [
            "project:mobile:android-components:releng:beetmover:action:push-to-maven",
            "project:mobile:android-components:releng:beetmover:bucket:maven-nightly-staging",
        ],
        "payload": {
            "version": "63.0.20201013153553",
            "artifactMap": [
                {"paths": {}, "locale": "en-US", "taskId": "AKjtHrqYQ32EDZ3GNzwXGg"},
                {
                    "paths": {
                        "public/build/browser-awesomebar-63.0.20201013153553.aar.asc": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.aar.asc"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553.pom.asc": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.pom.asc"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar.asc": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553-sources.jar.asc"
                            ],
                            "checksums_path": "",
                        },
                    },
                    "locale": "en-US",
                    "taskId": "ZYfA8OtXRZuDeF5Xq3ubxg",
                },
                {
                    "paths": {
                        "public/build/browser-awesomebar-63.0.20201013153553.aar": {
                            "destinations": ["maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.aar"],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553.pom": {
                            "destinations": ["maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.pom"],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553.aar.md5": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.aar.md5"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553.pom.md5": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.pom.md5"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553.aar.sha1": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.aar.sha1"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553.pom.sha1": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553.pom.sha1"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553-sources.jar"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar.md5": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553-sources.jar.md5"
                            ],
                            "checksums_path": "",
                        },
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar.sha1": {
                            "destinations": [
                                "maven2/org/mozilla/components/browser-awesomebar/63.0.20201013153553/browser-awesomebar-63.0.20201013153553-sources.jar.sha1"
                            ],
                            "checksums_path": "",
                        },
                    },
                    "locale": "en-US",
                    "taskId": "XGsGR0qdRmaWNE9fW5CmKQ",
                },
            ],
            "releaseProperties": {"appName": "nightly_components"},
            "upstreamArtifacts": [
                {
                    "paths": [
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar.asc",
                        "public/build/browser-awesomebar-63.0.20201013153553.aar.asc",
                        "public/build/browser-awesomebar-63.0.20201013153553.pom.asc",
                    ],
                    "taskId": "ZYfA8OtXRZuDeF5Xq3ubxg",
                    "taskType": "signing",
                },
                {
                    "paths": [
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar",
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar.md5",
                        "public/build/browser-awesomebar-63.0.20201013153553-sources.jar.sha1",
                        "public/build/browser-awesomebar-63.0.20201013153553.aar",
                        "public/build/browser-awesomebar-63.0.20201013153553.aar.md5",
                        "public/build/browser-awesomebar-63.0.20201013153553.aar.sha1",
                        "public/build/browser-awesomebar-63.0.20201013153553.pom",
                        "public/build/browser-awesomebar-63.0.20201013153553.pom.md5",
                        "public/build/browser-awesomebar-63.0.20201013153553.pom.sha1",
                    ],
                    "taskId": "XGsGR0qdRmaWNE9fW5CmKQ",
                    "taskType": "build",
                },
            ],
        },
    }


def create_dummy_artifacts_for_task(task, root_path):
    """Create artifacts to upload as specified in the given task."""
    for artifact_dict in task["payload"]["upstreamArtifacts"]:
        task_id = artifact_dict["taskId"]
        for path in artifact_dict["paths"]:
            full_path = root_path / task_id / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            create_dummy_artifact(full_path)


def create_dummy_artifact(file_path):
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


@pytest.fixture
def scriptworker_config(tmp_path, config, task):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    config["work_dir"] = str(work_dir)

    config_path = tmp_path / "config.json"
    with open(config_path, "w") as config_file:
        json.dump(config, config_file)

    with open(work_dir / "task.json", "w") as task_file:
        json.dump(task, task_file)

    create_dummy_artifacts_for_task(task, work_dir / "cot")

    return config_path


def test_main_android_components_nightly(scriptworker_config, task, boto3_client_mock, aiohttp_session_mock):
    main(config_path=scriptworker_config)

    # Number of artifacts put matches expected
    assert len(aiohttp_session_mock["put"]) == 12

    # Check paths
    expected_paths = get_paths_for_task(task)
    # Check that the destinations match exactly, and that they have been through signing
    expected_signed_paths = set(f"presigned_url+{dest}" for dest in expected_paths)
    assert expected_signed_paths == set(put_call["url"] for put_call in aiohttp_session_mock["put"])
    # Check that the source matches expected for every destination
    for put_call in aiohttp_session_mock["put"]:
        assert put_call["data"] == b"some data"
        _, unsigned_url = put_call["url"].split("+")
        assert put_call["source"].endswith(expected_paths[unsigned_url])
