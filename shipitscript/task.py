import json
import logging

import scriptworker.client
from scriptworker.utils import get_single_item_from_sequence

from shipitscript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)


# TODO: Make this prefix a param of the instance config, when Thunderbird migrates this task
_VALID_SCOPES_PREFIX = 'project:releng:ship-it:'


def validate_task_schema(context):
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)


def get_ship_it_instance_config_from_scope(context):
    scope = _get_scope(context.task)
    configured_instances = context.config['ship_it_instances']

    try:
        return configured_instances[scope]
    except KeyError:
        raise TaskVerificationError('This worker is not configured to handle scope "{}"'.format(scope))


def _get_scope(task):
    return get_single_item_from_sequence(
        task['scopes'],
        condition=lambda scope: scope.startswith(_VALID_SCOPES_PREFIX),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No valid scope found. Task must have a scope that starts with "{}"'.format(_VALID_SCOPES_PREFIX),
        too_many_item_error_message='More than one valid scope given',
    )
