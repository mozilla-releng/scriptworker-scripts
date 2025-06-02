import json
import os

import jsone
import jsonschema
import yaml

COMMON_CONTEXT = {"WORK_DIR": "/tmp/work", "VERBOSE": "true", "JARSIGNER_KEY_STORE": "keystore"}


def load_config(context):
    path_to_worker_template = os.path.join(os.path.dirname(__file__), "..", "docker.d", "worker.yml")
    with open(path_to_worker_template, "r") as file:
        worker_template = yaml.safe_load(file)

    return jsone.render(worker_template, context)


def load_schema():
    path_to_schema = os.path.join(os.path.dirname(__file__), "..", "src", "pushapkscript", "data", "config_schema.json")
    with open(path_to_schema, "r") as file:
        return json.load(file)


def _validate_config(context):
    context.update(COMMON_CONTEXT)
    config = load_config(context)
    schema = load_schema()

    jsonschema.validate(config, schema)


def test_mobile_prod():
    context = {
        "COT_PRODUCT": "mobile",
        "ENV": "prod",
        "GOOGLE_PLAY_SERVICE_ACCOUNT_FENIX_NIGHTLY": "nightly",
        "GOOGLE_CREDENTIALS_FENIX_NIGHTLY_PATH": "nightly",
        "GOOGLE_PLAY_SERVICE_ACCOUNT_FOCUS": "focus",
        "GOOGLE_CREDENTIALS_FOCUS_PATH": "focus",
        "GOOGLE_PLAY_SERVICE_ACCOUNT_FENIX_BETA": "beta",
        "GOOGLE_CREDENTIALS_FENIX_BETA_PATH": "beta",
        "GOOGLE_PLAY_SERVICE_ACCOUNT_FENIX_RELEASE": "release",
        "GOOGLE_CREDENTIALS_FENIX_RELEASE_PATH": "release",
        "GOOGLE_PLAY_SERVICE_ACCOUNT_REFERENCE_BROWSER": "reference-browser",
        "GOOGLE_CREDENTIALS_REFERENCE_BROWSER_PATH": "reference-browser",
    }
    _validate_config(context)


def test_mobile_fake_prod():
    context = {
        "COT_PRODUCT": "mobile",
        "ENV": "fake-prod",
        "GOOGLE_CREDENTIALS_FENIX_DEP_PATH": "fenix",
        "GOOGLE_CREDENTIALS_FOCUS_DEP_PATH": "focus",
        "GOOGLE_CREDENTIALS_REFERENCE_BROWSER_DEP_PATH": "reference-browser",
    }
    _validate_config(context)


def test_firefox_fake_prod():
    context = {
        "COT_PRODUCT": "firefox",
        "ENV": "fake-prod",
        "GOOGLE_CREDENTIALS_FENIX_DEP_PATH": "fenix",
        "GOOGLE_CREDENTIALS_FOCUS_DEP_PATH": "focus",
        "SGS_SERVICE_ACCOUNT_ID_DEP": "123456",
        "SGS_ACCESS_TOKEN_DEP": "abcdef",
    }
    _validate_config(context)


def test_firefox_prod():
    context = {
        "COT_PRODUCT": "firefox",
        "ENV": "prod",
        "GOOGLE_CREDENTIALS_FENIX_BETA_PATH": "beta",
        "GOOGLE_CREDENTIALS_FENIX_RELEASE_PATH": "release",
        "GOOGLE_CREDENTIALS_FENIX_NIGHTLY_PATH": "nightly",
        "GOOGLE_CREDENTIALS_FOCUS_PATH": "focus",
        "SGS_SERVICE_ACCOUNT_ID": "123456",
        "SGS_ACCESS_TOKEN": "abcdef",
    }
    _validate_config(context)
