"""Methods that deal with the task metadata to supply addonscript."""

import os

from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence


def get_channel(task):
    """Get the addon channel information from the task metadata.

    Assumes task['payload']['channel'] exists and is in the proper format.

    Args:
        task: the task definition.

    Returns:
        object: the tag info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If run without tag_info in task definition.

    """
    # XXX Per @escapewindow best to throw this piece onto a scope
    # ..:channel:{un,}listed and validate what uses it in scriptworker.
    channel = task.get("payload", {}).get("channel")
    if not channel:
        raise TaskVerificationError("Expected channel in payload")
    return channel


def build_filelist(context):
    """Build a list of cot-downloaded paths.

    Scriptworker will pre-download and pre-verify the `upstreamArtifacts`
    in our `work_dir`.  Let's build a list of relative of full paths.

    Args:
        context (SigningContext): the signing context

    Raises:
        TaskVerificationError: if the files don't exist on disk

    Returns:
        list: `full_path` of all files.

    """
    filelist = []
    messages = []
    for artifact_dict in context.task["payload"]["upstreamArtifacts"]:
        for path in artifact_dict["paths"]:
            full_path = os.path.join(context.config["work_dir"], "cot", artifact_dict["taskId"], path)
            if not os.path.exists(full_path):
                messages.append("{} doesn't exist!".format(full_path))
            filelist.append(full_path)
    if messages:
        raise TaskVerificationError(messages)
    return filelist


def get_amo_instance_config_from_scope(context):
    """Get instance configuration from task scope.

    Args:
        context (Context): the scriptworker context

    Raises:
        TaskVerificationError: if the task doesn't have the necessary scopes or if the instance
            isn't configured to process it

    Returns:
        dict: configuration, formatted like: {
            'amo_server': 'http://some-amo-it.url',
            'jwt_user': 'some-username',
            'jwt_secret': 'some-secret'
        }

    """
    scope = _get_scope(context.task)
    configured_instances = context.config["amo_instances"]

    try:
        return configured_instances[scope]
    except KeyError:
        raise TaskVerificationError('This worker is not configured to handle scope "{}"'.format(scope))


def _get_scope(context):
    scope_root = context.config["taskcluster_scope_prefix"]

    return get_single_item_from_sequence(
        context.task["scopes"],
        condition=lambda scope: scope.startswith(scope_root),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No valid scope found. Task must have a scope that starts with "{}"'.format(scope_root),
        too_many_item_error_message="More than one valid scope given",
    )
