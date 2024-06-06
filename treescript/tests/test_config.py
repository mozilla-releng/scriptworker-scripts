import json
import os

import jsone
import jsonschema
import pytest
import yaml


def load_config(context):
    path_to_worker_template = os.path.join(os.path.dirname(__file__), "..", "docker.d", "worker.yml")
    with open(path_to_worker_template, "r") as file:
        worker_template = yaml.safe_load(file)

    return jsone.render(worker_template, context)


def load_schema():
    path_to_schema = os.path.join(os.path.dirname(__file__), "..", "src", "treescript", "data", "config_schema.json")
    with open(path_to_schema, "r") as file:
        return json.load(file)


def _validate_config(context):
    config = load_config(context)
    schema = load_schema()

    jsonschema.validate(config, schema)


@pytest.mark.parametrize(
    "needs_hg,needs_git",
    (
        pytest.param(
            "1",
            "0",
            id="hg_only",
        ),
        pytest.param(
            "0",
            "1",
            id="git_only",
        ),
        pytest.param(
            "1",
            "1",
            id="hg_and_git",
        ),
    ),
)
def test_config(needs_hg, needs_git):
    context = {
        "WORK_DIR": "",
        "ARTIFACTS_DIR": "",
        "VERBOSE": "true",
        "UPSTREAM_REPO": "",
        "MERGE_DAY_CLOBBER_FILE": "",
        "COT_PRODUCT": "firefox",
        "TRUST_DOMAIN": "gecko",
        "NEEDS_HG": needs_hg,
        "NEEDS_GIT": needs_git,
        "ENV": "prod",
    }

    if needs_hg == "1":
        context["HG_SHARE_BASE_DIR"] = ""
        context["SSH_KEY_PATH"] = ""
        context["SSH_USER"] = ""
        context["SSH_MERGE_KEY_PATH"] = ""
        context["SSH_MERGE_USER"] = ""

    if needs_git == "1":
        context["GITHUB_PRIVKEY_FILE"] = ""

    _validate_config(context)
