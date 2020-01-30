import json
import os

import jsone
import jsonschema
import yaml

COMMON_CONTEXT = {"WORK_DIR": "", "ARTIFACTS_DIR": "", "VERBOSE": "true", "TASKCLUSTER_SCOPE_PREFIX": ""}


def load_config(context):
    path_to_worker_template = os.path.join(os.path.dirname(__file__), "..", "docker.d", "worker.yml")
    with open(path_to_worker_template, "r") as file:
        worker_template = yaml.safe_load(file)

    return jsone.render(worker_template, context)


def load_schema():
    path_to_schema = os.path.join(os.path.dirname(__file__), "..", "src", "bouncerscript", "data", "config_schema.json")
    with open(path_to_schema, "r") as file:
        return json.load(file)


def _validate_config(context):
    context.update(COMMON_CONTEXT)
    config = load_config(context)
    schema = load_schema()

    jsonschema.validate(config, schema)


def test_firefox_fake_prod():
    context = {
        "COT_PRODUCT": "firefox",
        "ENV": "fake-prod",
        "BOUNCER_USERNAME": "",
        "BOUNCER_PASSWORD": "",
        "BOUNCER_USERNAME_NAZGUL": "",
        "BOUNCER_PASSWORD_NAZGUL": "",
    }
    _validate_config(context)


def test_firefox_prod():
    context = {
        "COT_PRODUCT": "firefox",
        "ENV": "prod",
        "BOUNCER_USERNAME": "",
        "BOUNCER_PASSWORD": "",
        "BOUNCER_USERNAME_NAZGUL": "",
        "BOUNCER_PASSWORD_NAZGUL": "",
    }
    _validate_config(context)


def test_thunderbird_fake_prod():
    context = {
        "COT_PRODUCT": "thunderbird",
        "ENV": "fake-prod",
        "BOUNCER_USERNAME": "",
        "BOUNCER_PASSWORD": "",
        "BOUNCER_USERNAME_NAZGUL": "",
        "BOUNCER_PASSWORD_NAZGUL": "",
    }
    _validate_config(context)


def test_thunderbird_prod():
    context = {
        "COT_PRODUCT": "thunderbird",
        "ENV": "prod",
        "BOUNCER_USERNAME": "",
        "BOUNCER_PASSWORD": "",
        "BOUNCER_USERNAME_NAZGUL": "",
        "BOUNCER_PASSWORD_NAZGUL": "",
    }
    _validate_config(context)
