import json
import logging

import scriptworker.client

from shipitscript.exceptions import TaskVerificationError, BadInstanceConfigurationError
from shipitscript.utils import get_single_item_from_sequence

log = logging.getLogger(__name__)

ALLOWED_API_ROOT_PER_VALID_SCOPE = {
    'project:releng:ship-it:production': 'https://ship-it.mozilla.org',
    'project:releng:ship-it:staging': 'https://ship-it-dev.allizom.org',
    'project:releng:ship-it:dev': '*',
}

VALID_SCOPES = tuple(ALLOWED_API_ROOT_PER_VALID_SCOPE.keys())
PROTECTED_API_ROOTS = tuple([
    url
    for url in ALLOWED_API_ROOT_PER_VALID_SCOPE.values()
    if url != '*'
])


def validate_task_schema(context):
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)


def get_ship_it_instance_config_from_scope(context):
    scope = _get_scope(context.task)
    allowed_api_root = ALLOWED_API_ROOT_PER_VALID_SCOPE[scope]
    configured_instances = context.config['ship_it_instances']
    instance_type = scope.split(':')[-1]

    if allowed_api_root in PROTECTED_API_ROOTS:
        def condition(instance):
            return instance['api_root'].rstrip('/') == allowed_api_root
        no_item_error_message = 'This instance is now allowed to talk to the "{}" instance ({})'.format(
            instance_type, allowed_api_root
        )
    else:
        def condition(instance):
            return instance['api_root'].rstrip('/') not in PROTECTED_API_ROOTS
        no_item_error_message = "Couldn't find an API root that is not a protected one",

    return get_single_item_from_sequence(
        configured_instances,
        condition=condition,
        ErrorClass=BadInstanceConfigurationError,
        no_item_error_message=no_item_error_message,
        too_many_item_error_message='Too many "{}" instances configured'.format(instance_type, allowed_api_root),
        append_sequence_to_error_message=False
    )


def _get_scope(task):
    return get_single_item_from_sequence(
        task['scopes'],
        condition=lambda scope: scope in VALID_SCOPES,
        ErrorClass=TaskVerificationError,
        no_item_error_message='No valid scope found. Task must have one of these: {}'.format(VALID_SCOPES),
        too_many_item_error_message='More than one valid scope given',
    )
