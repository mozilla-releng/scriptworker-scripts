# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import os

import jsonschema

logger = logging.getLogger(__name__)

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "data", "builddecisionscript_task_schema.json")


def _load_schema():
    with open(_SCHEMA_PATH) as f:
        return json.load(f)


def validate_task_schema(task):
    schema = _load_schema()
    try:
        jsonschema.validate(task, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid task payload: {e.message}") from e


def get_payload(task):
    return task["payload"]
