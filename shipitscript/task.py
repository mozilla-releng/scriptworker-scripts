import json
import logging

import scriptworker.client

from shipitscript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)

ALLOWED_API_ROOT_PER_VALID_SCOPE = {
    'project:releng:scriptworker:ship-it:production': 'https://ship-it.mozilla.org',
    'project:releng:scriptworker:ship-it:staging': 'https://ship-it-dev.allizom.org',
    'project:releng:scriptworker:ship-it:dev': '*',
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


def validate_task_scope(context):
    scope = _get_scope(context.task)
    allowed_api_root = ALLOWED_API_ROOT_PER_VALID_SCOPE[scope]
    api_root_of_this_instance = context.config['ship_it_instance']['api_root']
    api_root_of_this_instance = api_root_of_this_instance.rstrip('/')
    if allowed_api_root != api_root_of_this_instance:
        if allowed_api_root in PROTECTED_API_ROOTS or api_root_of_this_instance in PROTECTED_API_ROOTS:
            instance_type = scope.split(':')[-1]
            raise TaskVerificationError(
                'This instance is now allowed to talk to the "{}" instance ({})'.format(instance_type, allowed_api_root)
            )


def _get_scope(task):
    given_scopes = task['scopes']
    scopes = [scope for scope in given_scopes if scope in VALID_SCOPES]

    number_of_scopes = len(scopes)
    if number_of_scopes == 0:
        raise TaskVerificationError(
            'No valid scope found. Task must have one of these: {}. Given scopes: {}'.format(VALID_SCOPES, given_scopes)
        )
    elif number_of_scopes > 1:
        raise TaskVerificationError('More than one valid scope given: {}'.format(scopes))

    return scopes[0]
