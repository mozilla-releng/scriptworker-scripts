#!/usr/bin/env python
"""Signingscript task functions.

Attributes:
    FORMAT_TO_SIGNING_FUNCTION (frozendict): a mapping between signing format
        and signing function. If not specified, use the `default` signing
        function.

"""
import json
import logging

import scriptworker.client

log = logging.getLogger(__name__)


# validate_task_schema {{{1
def validate_task_schema(context):
    """Validate the task json schema.

    Args:
        context (TreeContext): the tree context.

    Raises:
        ScriptWorkerTaskException: on failed validation.

    """
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)
