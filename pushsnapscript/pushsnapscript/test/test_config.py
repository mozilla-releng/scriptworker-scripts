import json
import os

import jsone
import jsonschema
import yaml

COMMON_CONTEXT = {
    'WORK_DIR': '',
    'ARTIFACTS_DIR': '',
    'VERBOSE': 'true',
}


def load_config(context):
    path_to_worker_template = os.path.join(os.path.dirname(__file__), '..', '..', 'docker.d', 'worker.yml')
    with open(path_to_worker_template, 'r') as file:
        worker_template = yaml.safe_load(file)

    return jsone.render(worker_template, context)


def load_schema():
    path_to_schema = os.path.join(os.path.dirname(__file__), '..', 'data', 'config_schema.json')
    with open(path_to_schema, 'r') as file:
        return json.load(file)


def _validate_config(context):
    context.update(COMMON_CONTEXT)
    config = load_config(context)
    schema = load_schema()

    jsonschema.validate(config, schema)


def test_fake_prod():
    context = {
        'ENV': 'fake-prod',
    }
    _validate_config(context)


def test_prod():
    context = {
        'ENV': 'prod',
        'MACAROON_BETA_PATH': '',
        'MACAROON_CANDIDATE_PATH': '',
        'MACAROON_ESR_PATH': '',
    }
    _validate_config(context)
