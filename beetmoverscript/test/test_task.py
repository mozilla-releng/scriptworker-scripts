import json
import os
import tempfile
from beetmoverscript.test import get_fake_valid_task, get_fake_valid_config, get_fake_balrog_props
from beetmoverscript.task import validate_task_schema, add_balrog_manifest_to_artifacts
from scriptworker.context import Context


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
