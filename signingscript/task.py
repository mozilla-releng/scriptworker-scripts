from jose import jwt
from jose.constants import ALGORITHMS
import json
import logging
import scriptworker.client
from signingscript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)


def task_cert_type(task):
    """Extract task certificate type"""
    certs = [s for s in task["scopes"] if
             s.startswith("project:releng:signing:cert:")]
    log.debug("Certificate types: %s", certs)
    if len(certs) != 1:
        raise TaskVerificationError("Only one certificate type can be used")
    return certs[0]


def task_signing_formats(task):
    """Extract last part of signing format scope"""
    return [s.split(":")[-1] for s in task["scopes"] if
            s.startswith("project:releng:signing:format:")]


def validate_signature(task_id, token, pub_key, algorithms=(ALGORITHMS.RS512, )):
    claims = jwt.decode(token, pub_key, algorithms=algorithms)
    if task_id != claims.get("taskId"):
        raise TaskVerificationError(
            "Task IDs do not match. Expected {}, got {}".format(task_id, claims.get("taskId"))
        )
    return claims


def validate_task_schema(context):
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_task_schema(context.task, task_schema)


def validate_task(context):
    validate_task_schema(context)
