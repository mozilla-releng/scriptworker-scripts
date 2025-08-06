import json
import os

import jsonschema
import pytest
import yaml

COMMON_CONTEXT = {"WORK_DIR": "", "ARTIFACTS_DIR": "", "VERBOSE": "true"}


@pytest.fixture(scope="module")
def task_definition():
    path_to_task_definition = os.path.join(os.path.dirname(__file__), "data", "task_example.yml")
    with open(path_to_task_definition, "r") as file:
        definition = yaml.safe_load(file)
    return definition


@pytest.fixture(scope="module")
def schema():
    path_to_schema = os.path.join(os.path.dirname(__file__), "..", "src", "iscript", "data", "i_task_schema.json")
    with open(path_to_schema, "r") as file:
        schema = json.load(file)
    return schema


def test_task_definition(task_definition, schema):
    jsonschema.validate(task_definition, schema)


def test_task_definition_empty_formats(task_definition, schema):
    task_definition["payload"]["upstreamArtifacts"][0]["formats"] = []
    jsonschema.validate(task_definition, schema)


def test_task_definition_invalid_formats(task_definition, schema):
    task_definition["payload"]["upstreamArtifacts"][0]["formats"] = ["invalid_format"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(task_definition, schema)
