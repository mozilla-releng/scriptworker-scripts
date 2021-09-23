import json
import os

import jsone
import jsonschema
import yaml


def load_config(context):
    path_to_worker_template = os.path.join(os.path.dirname(__file__), "..", "docker.d", "worker.yml")
    with open(path_to_worker_template, "r") as file:
        worker_template = yaml.safe_load(file)

    return jsone.render(worker_template, context)


def load_schema():
    path_to_schema = os.path.join(os.path.dirname(__file__), "..", "src", "balrogscript", "data", "config_schema.json")
    with open(path_to_schema, "r") as file:
        return json.load(file)


def _validate_config(context):
    config = load_config(context)
    schema = load_schema()

    jsonschema.validate(config, schema)


def test_config():
    context = {
        "WORK_DIR": "",
        "ARTIFACTS_DIR": "",
        "VERBOSE": "true",
        "TASKCLUSTER_SCOPE_PREFIX": "",
        "API_ROOT": "",
        "STAGE_API_ROOT": "",
        "AUTH0_DOMAIN": "",
        "AUTH0_CLIENT_ID": "",
        "AUTH0_CLIENT_SECRET": "",
        "AUTH0_AUDIENCE": "",
    }
    _validate_config(context)
