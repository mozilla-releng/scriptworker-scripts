import os
import json
from jsonschema import validate
from signingworker.exceptions import TaskVerificationError


def validate_task(task, supported_scopes):
    # TODO: verify source (signed payload?)
    task_schema = json.load(
        open(
            os.path.join(os.path.dirname(__file__),
                         "data", "signing_task_schema.json")
        )
    )
    validate(task, task_schema)
    if not set(task["scopes"]) & set(supported_scopes):
        raise TaskVerificationError(
            "No supported scopes ({}) defined in task's scopes ({})".format(
                supported_scopes, task["scopes"])
        )
