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


def get_config(scope_prefix):
    config = get_fake_valid_config()
    credentials = {"id": "dummy", "key": "dummy"}
    url_prefix = "https://url.prefix"
    config["taskcluster_scope_prefixes"] = [scope_prefix]
    config["bucket_config"] = {
        "maven-nightly-staging": {
            "buckets": {"nightly_components": "dummy"},
            "credentials": credentials,
            "url_prefix": url_prefix,
        },
        "maven-production": {
            "buckets": {"appservices": "dummy", "geckoview": "dummy", "telemetry": "dummy"},
            "credentials": credentials,
            "url_prefix": url_prefix,
        },
        "nightly": {
            "buckets": {"firefox": "dummy"},
            "credentials": credentials,
            "url_prefix": url_prefix,
        },
        "release": {
            "buckets": {"devedition": "dummy", "firefox": "dummy"},
            "credentials": credentials,
            "url_prefix": url_prefix,
        },
    }
    return config


def create_dummy_artifacts_for_task(task, root_path):
    """Create artifacts to upload as specified in the given task."""
    for artifact_dict in task["payload"].get("upstreamArtifacts", []):
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


def get_artifactmap_paths(task):
    return [path for artifact_dict in task["payload"]["upstreamArtifacts"] for path in artifact_dict["paths"]]


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
def boto3_resource_mock(monkeypatch):
    resource_mock = Mock(spec=beetmoverscript.script.boto3.resource("s3"))
    bucket_mock = Mock()

    def fake_bucket_objects_filter(**kwargs):
        prefix = kwargs["Prefix"]
        assert "candidates" in prefix or "releases" in prefix, f"prefix {prefix} should include 'candidates' or 'releases'"
        if "candidates" in prefix:
            return [Mock(key=f"{prefix}partner-repacks/mailru/okru/v1/", e_tag="dummy_etag")]
        elif "releases" in prefix:
            return []

    bucket_mock.objects.filter = fake_bucket_objects_filter

    resource_mock.Bucket.return_value = bucket_mock

    def fake_boto3_resource_only_s3(*args, **kwargs):
        assert args[0] == "s3", "A resource other than 's3' was requested"
        return resource_mock

    monkeypatch.setattr(beetmoverscript.script.boto3, "resource", fake_boto3_resource_only_s3)

    return resource_mock


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
    "task_name, scope_prefix, expected_number_of_moved_artifacts",
    (
        ("android_components_nightly", "project:mobile:android-components:releng:beetmover:", 12),
        ("application_services_release", "project:mozilla:app-services:releng:beetmover:", 12),
        ("geckoview_nightly", "project:releng:beetmover:", 16),
        ("glean_release", "project:mozilla:glean:releng:beetmover:", 20),
        ("firefox_desktop_nightly", "project:releng:beetmover:", 52),
        ("firefox_langpacks_beta", "project:releng:beetmover:", 1),
        ("firefox_generated_screenshots_release", "project:releng:beetmover:", 7),
    ),
)
def test_main_maven_nightly_candidates(task_name, scope_prefix, expected_number_of_moved_artifacts, tmp_path, boto3_client_mock, aiohttp_session_mock):
    config = get_config(scope_prefix)
    task = get_test_task(task_name)
    scriptworker_config = prepare_scriptworker_config(tmp_path, config, task)

    main(config_path=scriptworker_config)

    # Number of artifacts put matches expected
    assert len(aiohttp_session_mock["put"]) == expected_number_of_moved_artifacts

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


@pytest.mark.parametrize(
    "task_name, scope_prefix, expected_number_of_moved_artifacts",
    (("firefox_eme_free_release", "project:releng:beetmover:", 2),),
)
def test_main_push_to_partner(task_name, scope_prefix, expected_number_of_moved_artifacts, tmp_path, boto3_client_mock, aiohttp_session_mock):
    config = get_config(scope_prefix)
    task = get_test_task(task_name)
    scriptworker_config = prepare_scriptworker_config(tmp_path, config, task)

    main(config_path=scriptworker_config)

    # Number of artifacts put matches expected
    assert len(aiohttp_session_mock["put"]) == expected_number_of_moved_artifacts

    # Check paths. In this case the destinations are not included in the payload and their calculation is more
    # involved than in other cases, so to keep assertions simple we relax the conditions
    artifactmap_paths = get_artifactmap_paths(task)
    assert len(artifactmap_paths) == len(aiohttp_session_mock["put"])
    # Check that the source matches expected for every destination
    for put_call in aiohttp_session_mock["put"]:
        assert put_call["url"].startswith("presigned_url+")
        if not put_call["url"].endswith(".json"):
            assert put_call["data"] == b"some data"


def test_main_push_to_releases(tmp_path, boto3_client_mock, boto3_resource_mock):
    task_name = "firefox_release"
    scope_prefix = "project:releng:beetmover:"
    config = get_config(scope_prefix)
    task = get_test_task(task_name)
    scriptworker_config = prepare_scriptworker_config(tmp_path, config, task)

    main(config_path=scriptworker_config)

    assert boto3_client_mock.copy_object.call_count == 1
    boto3_client_mock.copy_object.assert_called_with(
        Bucket="dummy",
        CopySource={"Bucket": "dummy", "Key": "pub/firefox/candidates/82.0.2-candidates/build1/partner-repacks/mailru/okru/v1/"},
        Key="pub/firefox/releases/partners/mailru/okru/82.0.2/",
    )
