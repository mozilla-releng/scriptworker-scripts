import json
import os
import pytest
import tempfile
from beetmoverscript.test import (get_fake_valid_task, get_fake_valid_config,
                                  get_fake_balrog_props, get_fake_checksums_manifest)
from beetmoverscript.task import (validate_task_schema, add_balrog_manifest_to_artifacts,
                                  validate_task_scopes, get_upstream_artifacts,
                                  generate_checksums_manifest)
from beetmoverscript.utils import generate_beetmover_manifest
from scriptworker.context import Context


def test_validate_scopes():
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']
    context.artifacts_to_beetmove = get_upstream_artifacts(context)
    manifest = generate_beetmover_manifest(context.config, context.task, context.properties)

    context.task['scopes'] = []
    with pytest.raises(SystemExit):
        validate_task_scopes(context, manifest)

    context.task['scopes'] = ["project:releng:beetmover:mightly"]
    with pytest.raises(SystemExit):
        validate_task_scopes(context, manifest)

    context.task['scopes'] = ["project:releng:beetmover:dep"]
    manifest['s3_prefix_dated'] = "pub/mobile/nightly/2017/01/2017-01-dep.."
    manifest['s3_prefix_latest'] = "pub/mobile/nightly/2017/01/2017-01-dep.."

    with pytest.raises(SystemExit):
        validate_task_scopes(context, manifest)


def test_validate_task():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    validate_task_schema(context)


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


def test_checksums_manifest_generation():
    checksums = {
        "firefox-53.0a1.en-US.linux-i686.complete.mar": {
            "sha1": "332ab78ebd36e9217f451e1244",
            "sha512": "14f2d1cb999a8b42a3b6b671f7376c3e246daa65d108e2b8fe880f069601dc2b26afa155b52001235db059",
            "size": 618149,
            "md5": "073398e573e709",
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
