import os
import json
import logging
from jsonschema import validate
from signingworker.exceptions import TaskVerificationError

log = logging.getLogger(__name__)


def validate_task(task):
    # TODO: verify source (signed payload?)
    task_schema = json.load(
        open(
            os.path.join(os.path.dirname(__file__),
                         "data", "signing_task_schema.json")
        )
    )
    validate(task, task_schema)


def task_cert_type(task):
    """Extract task certificate type"""
    certs = [s for s in task["scopes"] if s.startswith("signing:cert:")]
    log.debug("Certificate types: %s", certs)
    if len(certs) != 1:
        raise TaskVerificationError("Only one certificate type can be used")
    return certs[0]


def task_signing_formats(task):
    """Extract last part of signing format scope"""
    return [s.split(":")[-1] for s in task["scopes"]
            if s.startswith("signing:format:")]
