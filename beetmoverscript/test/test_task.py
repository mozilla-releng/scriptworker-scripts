import json
import os
import pytest
import tempfile
from beetmoverscript.test import (
    context, get_fake_valid_task, get_fake_valid_config, get_fake_balrog_props,
    get_fake_checksums_manifest
)
from beetmoverscript.task import (
    validate_task_schema, add_balrog_manifest_to_artifacts,
    get_upstream_artifacts, generate_checksums_manifest,
    get_initial_release_props_file, get_task_bucket, get_task_action,
    validate_bucket_paths,
)
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

assert context  # silence pyflakes


# get_upstream_artifacts {{{1
def test_get_upstream_artifacts():
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']

    context.task['payload']['upstreamArtifacts'][0]['paths'].append('fake_file')
    with pytest.raises(ScriptWorkerTaskException):
        context.artifacts_to_beetmove = get_upstream_artifacts(context)


# validate_task {{{1
def test_validate_task(context):
    validate_task_schema(context)

    # release validation
    context.task['scopes'] = ["project:releng:beetmover:action:push-to-candidates"]
    context.task['payload'] = {
        'product': 'fennec',
        'build_number': 1,
        'version': '64.0b3',
    }
    validate_task_schema(context)


# get_task_bucket {{{1
@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:beetmover:bucket:dep", "project:releng:beetmover:bucket:release"],
    None, True,
), (
    ["project:releng:beetmover:bucket:!!"],
    None, True
), (
    ["project:releng:beetmover:bucket:dep", "project:releng:beetmover:action:foo"],
    "dep", False
)))
def test_get_task_bucket(scopes, expected, raises):
    task = {'scopes': scopes}
    config = {'bucket_config': {'dep': ''}}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_bucket(task, config)
    else:
        assert expected == get_task_bucket(task, config)


# get_task_action {{{1
@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:beetmover:action:dep", "project:releng:beetmover:action:release"],
    None, True
), (
    ["project:releng:beetmover:action:invalid"],
    None, True
), (
    ["project:releng:beetmover:action:dep"],
    "dep", False
)))
def test_get_task_action(scopes, expected, raises):
    task = {'scopes': scopes}
    config = {'actions': {'dep': ''}}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_action(task, config)
    else:
        assert expected == get_task_action(task, config)


@pytest.mark.parametrize("bucket,path,raises", ((
    "dep", "pub/devedition/nightly", False
), (
    "nightly", "pub/firefox/releases", True
)))
def test_validate_bucket_paths(bucket, path, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            validate_bucket_paths(bucket, path)
    else:
        validate_bucket_paths(bucket, path)


# balrog_manifest_to_artifacts {{{1
def test_balrog_manifest_to_artifacts():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()

    fake_balrog_manifest = get_fake_balrog_props()
    context.balrog_manifest = fake_balrog_manifest

    # fake the path to to able to check the contents written later on
    with tempfile.TemporaryDirectory() as tmpdirname:
        context.config['artifact_dir'] = tmpdirname
        file_path = os.path.join(context.config['artifact_dir'],
                                 'public/manifest.json')
        # <temp-dir>/public doesn't exist yet and it's not automatically
        # being created so we need to ensure it exists
        public_tmpdirname = os.path.join(tmpdirname, 'public')
        if not os.path.exists(public_tmpdirname):
            os.makedirs(public_tmpdirname)

        add_balrog_manifest_to_artifacts(context)

        with open(file_path, "r") as fread:
            retrieved_data = json.load(fread)

        assert fake_balrog_manifest == retrieved_data


# checksums_manifest_generation {{{1
def test_checksums_manifest_generation():
    checksums = {
        "firefox-53.0a1.en-US.linux-i686.complete.mar": {
            "sha512": "14f2d1cb999a8b42a3b6b671f7376c3e246daa65d108e2b8fe880f069601dc2b26afa155b52001235db059",
            "size": 618149,
            "sha256": "293975734953874539475"
        }
    }

    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.checksums = checksums

    expected_checksums_manifest_dump = get_fake_checksums_manifest()
    checksums_manifest_dump = generate_checksums_manifest(context)
    assert checksums_manifest_dump == expected_checksums_manifest_dump


# get_initial_release_props_file {{{1
def test_get_initial_release_props_file():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()

    context.task['payload']['upstreamArtifacts'] = [{'paths': []}]
    with pytest.raises(ScriptWorkerTaskException):
        get_initial_release_props_file(context)
