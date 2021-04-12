import json
import os

import jsone
import jsonschema
import yaml

COMMON_CONTEXT = {
    "WORK_DIR": "",
    "ARTIFACTS_DIR": "",
    "VERBOSE": "true",
    "PUBLIC_IP": "0.0.0.0",
    "PASSWORDS_PATH": "",
    "SSL_CERT_PATH": "",
    "SIGNTOOL_PATH": "",
    "DMG_PATH": "",
    "HFSPLUS_PATH": "",
    "ZIPALIGN_PATH": "",
    "GPG_PUBKEY_PATH": "",
    "WIDEVINE_CERT_PATH": "",
    "AUTHENTICODE_CERT_PATH": "",
    "AUTHENTICODE_CERT_PATH_202005": "",
    "AUTHENTICODE_CERT_PATH_202104": "",
    "AUTHENTICODE_CROSS_CERT_PATH": "",
    "AUTHENTICODE_TIMESTAMP_STYLE": "",
}


def load_config(path_to_template, context):
    with open(path_to_template, "r") as file:
        worker_template = yaml.safe_load(file)

    return jsone.render(worker_template, context)


def load_schema(path_to_schema):
    with open(path_to_schema, "r") as file:
        return json.load(file)


def _validate_config(context):
    context.update(COMMON_CONTEXT)
    config = load_config(os.path.join(os.path.dirname(__file__), "..", "docker.d", "worker.yml"), context)
    passwords_config = load_config(os.path.join(os.path.dirname(__file__), "..", "docker.d", "passwords.yml"), context)
    config_schema = load_schema(os.path.join(os.path.dirname(__file__), "..", "src", "signingscript", "data", "config_schema.json"))
    passwords_schema = load_schema(os.path.join(os.path.dirname(__file__), "..", "src", "signingscript", "data", "passwords_config_schema.json"))

    jsonschema.validate(config, config_schema)
    jsonschema.validate(passwords_config, passwords_schema)


def test_firefox_dev():
    context = {
        "COT_PRODUCT": "firefox",
        "ENV": "dev",
        "AUTOGRAPH_AUTHENTICODE_USERNAME": "",
        "AUTOGRAPH_AUTHENTICODE_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME": "",
        "AUTOGRAPH_FENNEC_USERNAME": "",
        "AUTOGRAPH_FENNEC_PASSWORD": "",
        "AUTOGRAPH_MAR_USERNAME": "",
        "AUTOGRAPH_MAR_PASSWORD": "",
        "AUTOGRAPH_MAR_STAGE_USERNAME": "",
        "AUTOGRAPH_MAR_STAGE_PASSWORD": "",
        "AUTOGRAPH_GPG_USERNAME": "",
        "AUTOGRAPH_GPG_PASSWORD": "",
        "AUTOGRAPH_WIDEVINE_USERNAME": "",
        "AUTOGRAPH_WIDEVINE_PASSWORD": "",
        "AUTOGRAPH_OMNIJA_USERNAME": "",
        "AUTOGRAPH_OMNIJA_PASSWORD": "",
        "AUTOGRAPH_LANGPACK_USERNAME": "",
        "AUTOGRAPH_LANGPACK_PASSWORD": "",
    }
    _validate_config(context)


def test_thunderbird_fake_prod():
    context = {
        "COT_PRODUCT": "thunderbird",
        "ENV": "fake-prod",
        "AUTOGRAPH_AUTHENTICODE_USERNAME": "",
        "AUTOGRAPH_AUTHENTICODE_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME": "",
        "AUTOGRAPH_FENNEC_USERNAME": "",
        "AUTOGRAPH_FENNEC_PASSWORD": "",
        "AUTOGRAPH_MAR_USERNAME": "",
        "AUTOGRAPH_MAR_PASSWORD": "",
        "AUTOGRAPH_MAR_STAGE_USERNAME": "",
        "AUTOGRAPH_MAR_STAGE_PASSWORD": "",
        "AUTOGRAPH_GPG_USERNAME": "",
        "AUTOGRAPH_GPG_PASSWORD": "",
        "AUTOGRAPH_WIDEVINE_USERNAME": "",
        "AUTOGRAPH_WIDEVINE_PASSWORD": "",
        "AUTOGRAPH_OMNIJA_USERNAME": "",
        "AUTOGRAPH_OMNIJA_PASSWORD": "",
        "AUTOGRAPH_LANGPACK_USERNAME": "",
        "AUTOGRAPH_LANGPACK_PASSWORD": "",
    }
    _validate_config(context)


def test_mobile_fake_prod():
    context = {
        "COT_PRODUCT": "mobile",
        "ENV": "fake-prod",
        "AUTOGRAPH_FOCUS_USERNAME": "",
        "AUTOGRAPH_FOCUS_PASSWORD": "",
        "AUTOGRAPH_FENIX_USERNAME": "",
        "AUTOGRAPH_FENIX_PASSWORD": "",
        "AUTOGRAPH_REFERENCE_BROWSER_USERNAME": "",
        "AUTOGRAPH_REFERENCE_BROWSER_PASSWORD": "",
        "AUTOGRAPH_GPG_USERNAME": "",
        "AUTOGRAPH_GPG_PASSWORD": "",
    }
    _validate_config(context)


def test_application_services_fake_prod():
    context = {"COT_PRODUCT": "app-services", "ENV": "fake-prod", "AUTOGRAPH_GPG_USERNAME": "", "AUTOGRAPH_GPG_PASSWORD": ""}
    _validate_config(context)


def test_firefox_prod():
    context = {
        "COT_PRODUCT": "firefox",
        "ENV": "prod",
        "AUTOGRAPH_AUTHENTICODE_USERNAME": "",
        "AUTOGRAPH_AUTHENTICODE_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME": "",
        "AUTOGRAPH_MAR_RELEASE_USERNAME": "",
        "AUTOGRAPH_MAR_RELEASE_PASSWORD": "",
        "AUTOGRAPH_FENNEC_RELEASE_USERNAME": "",
        "AUTOGRAPH_FENNEC_RELEASE_PASSWORD": "",
        "AUTOGRAPH_GPG_USERNAME": "",
        "AUTOGRAPH_GPG_PASSWORD": "",
        "AUTOGRAPH_WIDEVINE_USERNAME": "",
        "AUTOGRAPH_WIDEVINE_PASSWORD": "",
        "AUTOGRAPH_OMNIJA_USERNAME": "",
        "AUTOGRAPH_OMNIJA_PASSWORD": "",
        "AUTOGRAPH_LANGPACK_USERNAME": "",
        "AUTOGRAPH_LANGPACK_PASSWORD": "",
        "AUTOGRAPH_MAR_NIGHTLY_USERNAME": "",
        "AUTOGRAPH_MAR_NIGHTLY_PASSWORD": "",
        "AUTOGRAPH_FENNEC_NIGHTLY_USERNAME": "",
        "AUTOGRAPH_FENNEC_NIGHTLY_PASSWORD": "",
    }
    _validate_config(context)


def test_thunderbird_prod():
    context = {
        "COT_PRODUCT": "thunderbird",
        "ENV": "prod",
        "AUTOGRAPH_AUTHENTICODE_USERNAME": "",
        "AUTOGRAPH_AUTHENTICODE_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD": "",
        "AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME": "",
        "AUTOGRAPH_MAR_RELEASE_USERNAME": "",
        "AUTOGRAPH_MAR_RELEASE_PASSWORD": "",
        "AUTOGRAPH_FENNEC_RELEASE_USERNAME": "",
        "AUTOGRAPH_FENNEC_RELEASE_PASSWORD": "",
        "AUTOGRAPH_GPG_USERNAME": "",
        "AUTOGRAPH_GPG_PASSWORD": "",
        "AUTOGRAPH_WIDEVINE_USERNAME": "",
        "AUTOGRAPH_WIDEVINE_PASSWORD": "",
        "AUTOGRAPH_OMNIJA_USERNAME": "",
        "AUTOGRAPH_OMNIJA_PASSWORD": "",
        "AUTOGRAPH_LANGPACK_USERNAME": "",
        "AUTOGRAPH_LANGPACK_PASSWORD": "",
        "AUTOGRAPH_MAR_NIGHTLY_USERNAME": "",
        "AUTOGRAPH_MAR_NIGHTLY_PASSWORD": "",
        "AUTOGRAPH_FENNEC_NIGHTLY_USERNAME": "",
        "AUTOGRAPH_FENNEC_NIGHTLY_PASSWORD": "",
    }
    _validate_config(context)


def test_mobile_prod():
    context = {
        "COT_PRODUCT": "mobile",
        "ENV": "prod",
        "AUTOGRAPH_FOCUS_USERNAME": "",
        "AUTOGRAPH_FOCUS_PASSWORD": "",
        "AUTOGRAPH_FENIX_NIGHTLY_USERNAME": "",
        "AUTOGRAPH_FENIX_NIGHTLY_PASSWORD": "",
        "AUTOGRAPH_FENIX_BETA_USERNAME": "",
        "AUTOGRAPH_FENIX_BETA_PASSWORD": "",
        "AUTOGRAPH_FENIX_USERNAME": "",
        "AUTOGRAPH_FENIX_PASSWORD": "",
        "AUTOGRAPH_FENNEC_NIGHTLY_USERNAME": "",
        "AUTOGRAPH_FENNEC_NIGHTLY_PASSWORD": "",
        "AUTOGRAPH_FENNEC_RELEASE_USERNAME": "",
        "AUTOGRAPH_FENNEC_RELEASE_PASSWORD": "",
        "AUTOGRAPH_FIREFOX_TV_USERNAME": "",
        "AUTOGRAPH_FIREFOX_TV_PASSWORD": "",
        "AUTOGRAPH_REFERENCE_BROWSER_USERNAME": "",
        "AUTOGRAPH_REFERENCE_BROWSER_PASSWORD": "",
        "AUTOGRAPH_GPG_USERNAME": "",
        "AUTOGRAPH_GPG_PASSWORD": "",
    }
    _validate_config(context)


def test_application_services_prod():
    context = {"COT_PRODUCT": "app-services", "ENV": "prod", "AUTOGRAPH_GPG_USERNAME": "", "AUTOGRAPH_GPG_PASSWORD": ""}
    _validate_config(context)
