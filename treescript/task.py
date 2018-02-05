#!/usr/bin/env python
"""Treescript task functions."""
import json
import logging

import scriptworker.client

from treescript.exceptions import TaskVerificationError

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


def get_source_repo(task):
    """Get the source repo from the task metadata.

    Assumes task['metadata']['source'] exists and is a link to a mercurial file on
    hg.mozilla.org (over https)

    Args:
        task: the task definition.

    Returns:
        str: url, including https scheme, to mercurial repository of the source repo.

    Raises:
        TaskVerificationError: on unexpected input.

    """
    source = task.get("metadata", {}).get("source", None)
    if not source:
        raise TaskVerificationError("No source, how did that happen")
    if not source.startswith("https://hg.mozilla.org/"):
        raise TaskVerificationError("Unable to operate on sources not in hg.mozilla.org")
    parts = source.split('/file/')
    if len(parts) < 2:
        raise TaskVerificationError("Soure url is in unexpected format")
    return parts[0]
