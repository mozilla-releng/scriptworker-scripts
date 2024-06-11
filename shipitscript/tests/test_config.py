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
    path_to_schema = os.path.join(os.path.dirname(__file__), "..", "src", "shipitscript", "data", "config_schema.json")
    with open(path_to_schema, "r") as file:
        return json.load(file)


def _validate_config(context):
    config = load_config(context)
    schema = load_schema()

    jsonschema.validate(config, schema)


def test_config():
    context = {
        "WORK_DIR": "",
        "VERBOSE": "true",
        "TASKCLUSTER_SCOPE_PREFIX": "",
        "MARK_AS_SHIPPED_SCHEMA_FILE": "",
        "TASKCLUSTER_SCOPE": "",
        "API_ROOT_V2": "",
        "TASKCLUSTER_CLIENT_ID": "",
        "TASKCLUSTER_ACCESS_TOKEN": "",
        "CREATE_NEW_RELEASE_SCHEMA_FILE": "",
        "UPDATE_PRODUCT_CHANNEL_VERSION_SCHEMA_FILE": "",
    }
    _validate_config(context)
