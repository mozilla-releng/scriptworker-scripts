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
    validate_bucket_paths, get_release_props
)
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.utils import makedirs

assert context  # silence pyflakes


# get_upstream_artifacts {{{1
def test_exception_get_upstream_artifacts():
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']

    context.task['payload']['upstreamArtifacts'][0]['paths'].append('fake_file')
    with pytest.raises(ScriptWorkerTaskException):
        context.artifacts_to_beetmove = get_upstream_artifacts(context)


# get_upstream_artifacts {{{1
@pytest.mark.parametrize("expected, preserve", ((
    ['target.txt',
     'target.mozinfo.json',
     'target_info.txt',
     'target.test_packages.json'], False
), (
    ['public/build/target.txt',
     'public/build/target.mozinfo.json',
     'public/build/target_info.txt',
     'public/build/target.test_packages.json'], True
)))
def test_get_upstream_artifacts(expected, preserve):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']

    artifacts_to_beetmove = get_upstream_artifacts(context, preserve_full_paths=preserve)
    assert sorted(list(artifacts_to_beetmove['en-US'])) == sorted(expected)


# validate_task {{{1
def test_validate_task(context):
    validate_task_schema(context)

    # release validation
    context.task['scopes'] = ["project:releng:beetmover:action:push-to-releases"]
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
    config = {'bucket_config': {'dep': ''}, 'taskcluster_scope_prefix': 'project:releng:beetmover:'}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_bucket(task, config)
    else:
        assert expected == get_task_bucket(task, config)


# get_task_action {{{1
@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:beetmover:action:push-to-nightly", "project:releng:beetmover:action:invalid"],
    None, True
), (
    ["project:releng:beetmover:action:invalid"],
    None, True
), (
    ["project:releng:beetmover:action:push-to-nightly"],
    "push-to-nightly", False
)))
def test_get_task_action(scopes, expected, raises):
    task = {'scopes': scopes}
    config = {'actions': {'dep': ''}, 'taskcluster_scope_prefix': 'project:releng:beetmover:'}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_action(task, config)
    else:
        assert expected == get_task_action(task, config)


# validate_bucket_paths {{{1
@pytest.mark.parametrize("bucket,path,raises", ((
    "dep", "pub/mobile/nightly", False
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


# get_release_props {{{1
@pytest.mark.parametrize("taskjson,locale, relprops, expected", ((
    'task.json', False, {
        "platform": "android",
        "stage_platform": "android-api-16"
    }, {
        "platform": "android-api-16",
        "stage_platform": "android-api-16"
    }
), (
    'task.json', True, {
        "platform": "macosx64",
    }, {
        "platform": "mac",
        "stage_platform": "macosx64"
    }
), (
    'task.json', False, {
        "platform": "linux64",
        "stage_platform": "linux64"
    }, {
        "platform": "linux-x86_64",
        "stage_platform": "linux64"
    }
), (
    'task_devedition.json', False, {
        "platform": "macosx64",
        "stage_platform": "macosx64-devedition"
    }, {
        "platform": "mac",
        "stage_platform": "macosx64-devedition"
    }
), (
    'task_devedition.json', True, {
        "platform": "win64",
    }, {
        "platform": "win64",
        "stage_platform": "win64-devedition"
    }
)))
def test_get_release_props(context, mocker, taskjson, locale, relprops, expected):
    context.task = get_fake_valid_task(taskjson)
    if locale:
        context.task['payload']['locale'] = 'lang'

    context.task['payload']['releaseProperties'] = relprops
    assert get_release_props(context) == (expected, None)

    # also check balrog_props method works with same data
    # TODO remove the end of this function when method is not supported anymore
    del context.task['payload']['releaseProperties']

    context.task['payload']['upstreamArtifacts'] = [{
      "locale": "lang",
      "paths": [
        "public/build/lang/balrog_props.json"
      ],
      "taskId": "buildTaskId",
      "taskType": "build"
    }]

    balrog_props_path = os.path.abspath(os.path.join(context.config['work_dir'], 'cot', 'buildTaskId', 'public/build/lang/balrog_props.json'))
    makedirs(os.path.dirname(balrog_props_path))
    with open(balrog_props_path, 'w') as f:
        json.dump({
            'properties': relprops
        }, f)

    assert get_release_props(context) == (expected, balrog_props_path)


# get_initial_release_props_file {{{1
def test_get_initial_release_props_file():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()

    context.task['payload']['upstreamArtifacts'] = [{'paths': []}]
    with pytest.raises(ScriptWorkerTaskException):
        get_initial_release_props_file(context)
