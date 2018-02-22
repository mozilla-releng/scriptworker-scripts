import json
import logging
import re

import scriptworker.client
from scriptworker.exceptions import ScriptWorkerTaskException

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

    if server_scope not in script_config['bouncer_instances']:
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
    if action not in script_config['actions']:
        messages.append("Invalid action scope")

    if messages:
        raise ScriptWorkerTaskException('\n'.join(messages))

    return action


def validate_task_schema(context, schema):
    """Perform a schema validation check against taks definition"""
    schema_file = context.config['schema_files'][schema]
    with open(schema_file) as fh:
        task_schema = json.load(fh)
    scriptworker.client.validate_json_schema(context.task, task_schema)
