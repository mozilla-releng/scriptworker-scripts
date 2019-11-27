import logging

from scriptworker import client
from scriptworker.exceptions import ScriptWorkerTaskException, TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

log = logging.getLogger(__name__)

# SCHEMA_MAP {{{1
SCHEMA_MAP = {
    'mark-as-shipped': 'mark_as_shipped_schema_file',
    'create-new-release': 'create_new_release_schema_file',
}


def _get_scope(context, suffix):
    scope_root = context.config["taskcluster_scope_prefix"] + suffix

    return get_single_item_from_sequence(
        context.task['scopes'],
        condition=lambda scope: scope.startswith(scope_root),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No valid scope found. Task must have a scope that starts with "{}"'.format(
            scope_root
        ),
        too_many_item_error_message='More than one valid scope given',
    )


def get_ship_it_instance_config_from_scope(context):
    scope = _get_scope(context, "server")
    configured_instance = context.config['shipit_instance']

    if configured_instance.get('scope') == scope:
        return configured_instance

    raise TaskVerificationError(
        'This worker is not configured to handle scope "{}"'.format(scope)
    )


def validate_task_schema(context):
    """Perform a schema validation check against taks definition"""
    action = get_task_action(context)
    schema_key = SCHEMA_MAP.get(action)
    client.validate_task_schema(context, schema_key=schema_key)


def get_task_action(context):
    """Extract last part of shipit action scope"""
    scope = _get_scope(context, "action")
    action = scope.split(":")[-1]

    # SCHEMA_MAP and ACTION_MAP share the keys as being the action scopes
    if action not in SCHEMA_MAP:
        raise ScriptWorkerTaskException("Invalid action scope: {}".format(action))

    return action
