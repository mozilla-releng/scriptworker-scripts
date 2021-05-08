import json
import os

import jsone
import jsonschema
import yaml

COMMON_CONTEXT = {"WORK_DIR": "", "ARTIFACTS_DIR": "", "VERBOSE": "true"}


def load_config(context):
    path_to_worker_template = os.path.join(os.path.dirname(__file__), "..", "docker.d", "worker.yml")
    with open(path_to_worker_template, "r") as file:
        worker_template = yaml.safe_load(file)

    return jsone.render(worker_template, context)


def load_schema():
    path_to_schema = os.path.join(os.path.dirname(__file__), "..", "src", "beetmoverscript", "data", "config_schema.json")
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
        "DEP_ID": "",
        "DEP_KEY": "",
        "DEP_PARTNER_ID": "",
        "DEP_PARTNER_KEY": "",
        "MAVEN_ID": "",
        "MAVEN_KEY": "",
    }
    _validate_config(context)


def test_firefox_prod():
    context = {
        "COT_PRODUCT": "firefox",
        "ENV": "prod",
        "NIGHTLY_ID": "",
        "NIGHTLY_KEY": "",
        "RELEASE_ID": "",
        "RELEASE_KEY": "",
        "PARTNER_ID": "",
        "PARTNER_KEY": "",
        "DEP_ID": "",
        "DEP_KEY": "",
        "DEP_PARTNER_ID": "",
        "DEP_PARTNER_KEY": "",
        "MAVEN_ID": "",
        "MAVEN_KEY": "",
    }
    _validate_config(context)


def test_thunderbird_fake_prod():
    context = {"COT_PRODUCT": "thunderbird", "ENV": "fake-prod", "DEP_ID": "", "DEP_KEY": ""}
    _validate_config(context)


def test_thunderbird_prod():
    context = {
        "COT_PRODUCT": "thunderbird",
        "ENV": "prod",
        "NIGHTLY_ID": "",
        "NIGHTLY_KEY": "",
        "RELEASE_ID": "",
        "RELEASE_KEY": "",
        "DEP_ID": "",
        "DEP_KEY": "",
    }
    _validate_config(context)


def test_mobile_fake_prod():
    context = {
        "COT_PRODUCT": "mobile",
        "ENV": "fake-prod",
        "MAVEN_ID": "",
        "MAVEN_KEY": "",
        "MAVEN_NIGHTLY_ID": "",
        "MAVEN_NIGHTLY_KEY": "",
    }
    _validate_config(context)


def test_mobile_prod():
    context = {
        "COT_PRODUCT": "mobile",
        "ENV": "prod",
        "MAVEN_ID": "",
        "MAVEN_KEY": "",
        "MAVEN_NIGHTLY_ID": "",
        "MAVEN_NIGHTLY_KEY": "",
    }
    _validate_config(context)


def test_application_services_fake_prod():
    context = {"COT_PRODUCT": "app-services", "ENV": "fake-prod", "MAVEN_ID": "", "MAVEN_KEY": ""}
    _validate_config(context)


def test_application_services_prod():
    context = {"COT_PRODUCT": "app-services", "ENV": "prod", "MAVEN_ID": "", "MAVEN_KEY": ""}
    _validate_config(context)
