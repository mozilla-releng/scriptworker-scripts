import os
from copy import deepcopy
from typing import Any

from scriptworker_client.exceptions import TaskVerificationError
from scriptworker_client.utils import get_single_item_from_sequence


def _deep_merge_dict(source: dict, dest: dict) -> dict:
    """Deep merge two dictionaries.

    Copied from taskgraph.utils.templates.merge_to
    https://github.com/taskcluster/taskgraph/blob/main/src/taskgraph/util/templates.py

    Args:
        source (dict): The base dictionary to be copied from.
        dest (dict): The destinatioon dictionary modified.
    """
    for key, value in source.items():
        # Override mismatching or empty types
        if type(value) != type(dest.get(key)):  # noqa: E721
            dest[key] = source[key]
            continue

        # Merge dict
        if isinstance(value, dict):
            _deep_merge_dict(value, dest[key])
            continue

        # Merge list
        if isinstance(value, list):
            dest[key] = dest[key] + source[key]
            continue

        dest[key] = source[key]

    return dest


# Build params that bitrisescript derives from the task's scopes. Letting the task
# payload set these would bypass the scope checks these values come from.
SCOPE_DERIVED_BUILD_PARAMS = ("workflow_id",)


def _reject_scope_derived_build_params(params: dict[str, Any], payload_key: str) -> None:
    """Reject build params that bitrisescript derives from the task's scopes.

    Args:
        params (dict): Build params supplied by the task payload.
        payload_key (str): The payload key ``params`` was read from, used in the
            error message.

    Raises:
        TaskVerificationError: If ``params`` sets a scope derived build param.
    """
    reserved = sorted(set(params) & set(SCOPE_DERIVED_BUILD_PARAMS))
    if reserved:
        raise TaskVerificationError(f"Param(s) {reserved} in '{payload_key}' are derived from the task's scopes and cannot be set by the task payload")


def _get_allowed_scope_prefixes(config):
    prefixes = config["taskcluster_scope_prefixes"]
    return [prefix if prefix.endswith(":") else "{}:".format(prefix) for prefix in prefixes]


def extract_common_scope_prefix(config: dict[str, Any], task: dict[str, Any]) -> str:
    """Extract common scope prefix.

    Args:
        config (dict): The bitrisescript config.
        task (dict): The task definition.
    """
    prefixes = _get_allowed_scope_prefixes(config)
    scopes = task["scopes"]

    found_prefixes = {prefix for prefix in prefixes for scope in scopes if scope.startswith(prefix)}

    return get_single_item_from_sequence(
        sequence=found_prefixes,
        condition=lambda _: True,
        ErrorClass=TaskVerificationError,
        no_item_error_message=f"No scope starting with any of these prefixes {prefixes} found",
        too_many_item_error_message="Too many prefixes found",
    )


def _extract_last_chunk_of_scope(scope: str, prefix: str) -> str:
    last_chunk = scope.split(":")[prefix.count(":") :]  # the chunk after the prefix is the product name
    return ":".join(last_chunk)


def get_bitrise_app(config: dict[str, Any], task: dict[str, Any]) -> str:
    """Get the bitrise app to target.

    The app is extacted from the task's scopes.

    Args:
        config (dict): The bitrisescript config.
        task (dict): The task definition.

    Returns:
        str: The bitrise app to target.

    Raises:
        TaskVerificationError: If task is missing the app scope or has more
        than one app scope.
    """
    prefix = extract_common_scope_prefix(config, task)
    app_prefix = f"{prefix}app:"
    scope = get_single_item_from_sequence(
        sequence=task["scopes"],
        condition=lambda scope: scope.startswith(app_prefix),
        ErrorClass=TaskVerificationError,
        no_item_error_message=f'No scope starting with any of this prefix "{prefix}" found',
        too_many_item_error_message=f'Too many scopes with this prefix "{prefix}" found',
    )

    return _extract_last_chunk_of_scope(scope, app_prefix)


def get_bitrise_workflows(config: dict[str, Any], task: dict[str, Any]) -> list[str]:
    """Get the bitrise workflows to run.

    Workflows are extacted from the task's scopes.

    Args:
        config (dict): The bitrisescript config.
        task (dict): The task definition.

    Returns:
        list: A list of bitrise workflows that should be scheduled.
    """
    prefix = extract_common_scope_prefix(config, task)
    workflow_prefix = f"{prefix}workflow:"
    workflows = [_extract_last_chunk_of_scope(scope, workflow_prefix) for scope in task["scopes"] if scope.startswith(workflow_prefix)]

    if not workflows:
        raise TaskVerificationError(f"No workflow scopes starting with '{prefix}' found")
    return workflows


def get_build_params(task: dict[str, Any], workflow: str = None) -> list[dict[str, Any]]:
    """Get the build_params from the task payload or an empty dict.

    Args:
        task (dict): The task definition.
        workflow (str): Optional workflow reference used to load workflow_params

    Returns:
        list: The list of bitrise build_params to specify. Always sets
            workflow_id to `workflow` on each returned dict.

    Raises:
        TaskVerificationError: If the task payload sets a scope derived build param.
    """
    global_params = task["payload"].get("global_params", {})
    _reject_scope_derived_build_params(global_params, "global_params")

    workflow_params = task["payload"].get("workflow_params", {}).get(workflow)
    if not workflow_params:
        return [{**global_params, "workflow_id": workflow}]

    build_params = []
    for variation in workflow_params:
        _reject_scope_derived_build_params(variation, f"workflow_params.{workflow}")
        params = _deep_merge_dict(variation, deepcopy(global_params))
        # workflow_id comes from the task's scopes, so it is set after the merge
        # rather than merged over by the payload.
        params["workflow_id"] = workflow
        build_params.append(params)
    return build_params


def get_artifact_dir(config: dict[str, Any], task: dict[str, Any]) -> str:
    """Get the directory to store artifacts from the config and task payload.

    Args:
        task (dict): The task definition.

    Returns:
        str: The directory to store artifacts.
    """
    artifact_prefix = task["payload"].get("artifact_prefix", "")
    artifact_dir = os.path.normpath(os.path.join(config["artifact_dir"], artifact_prefix))
    if not artifact_dir.startswith(config["artifact_dir"]):
        raise TaskVerificationError(f"{artifact_dir} is not a subdirectory of {config['artifact_dir']}!")

    return artifact_dir
