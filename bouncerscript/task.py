import logging
import re

from scriptworker import client
from scriptworker.exceptions import (
    ScriptWorkerTaskException, TaskVerificationError
)
from bouncerscript.constants import ALIASES_REGEXES

log = logging.getLogger(__name__)


def get_task_server(task, script_config):
    """Extract task server scope from scopes"""
    server_scopes = [s for s in task["scopes"] if
                     s.startswith("project:releng:bouncer:server:")]
    log.info("Servers scopes: %s", server_scopes)
    messages = []

    if len(server_scopes) != 1:
        messages.append("One and only one server can be used")
    server_scope = server_scopes[0]
    server = server_scope.split(':')[-1]
    if re.search('^[0-9A-Za-z_-]+$', server) is None:
        messages.append("Server {} is malformed".format(server))

    if server_scope not in script_config['bouncer_config']:
        messages.append("Invalid server scope")

    if messages:
        raise ScriptWorkerTaskException('\n'.join(messages))

    return server_scope


def get_task_action(task, script_config):
    """Extract last part of bouncer action scope"""
    actions = [s.split(":")[-1] for s in task["scopes"] if
               s.startswith("project:releng:bouncer:action:")]

    log.info("Action types: %s", actions)
    messages = []
    if len(actions) != 1:
        messages.append("One and only one action type can be used")

    action = actions[0]
    if action not in get_supported_actions(script_config):
        messages.append("Invalid action scope")

    if messages:
        raise ScriptWorkerTaskException('\n'.join(messages))

    return action


def matches(name, pattern):
    return re.match(pattern, name)


def get_supported_actions(script_config):
    return tuple(script_config['schema_files'].keys())


def validate_task_schema(context):
    """Perform a schema validation check against taks definition"""
    action = get_task_action(context.task, context.config)
    schema_key = "schema_files.{}".format(action)
    client.validate_task_schema(context, schema_key=schema_key)


def check_product_names_match_aliases(context):
    """Make sure we don't do any cross-product/channel alias update"""
    aliases = context.task["payload"]["aliases_entries"]

    validations = []
    for alias, product_name in aliases.items():
        if alias not in ALIASES_REGEXES.keys():
            raise TaskVerificationError("Unrecognized alias:{}".format(alias))

        validations.append(matches(product_name, ALIASES_REGEXES[alias]))

    if not all(validations):
        raise TaskVerificationError("The product/alias pairs are corrupt: {}".format(aliases))
