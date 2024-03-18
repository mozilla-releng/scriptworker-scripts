from typing import Any

from scriptworker_client.exceptions import TaskVerificationError
from scriptworker_client.utils import get_single_item_from_sequence


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


def get_build_params(task: dict[str, Any]) -> dict[str, Any]:
    """Get the build_params from the task payload or an empty dict.

    Args:
        task (dict): The task definition.

    Returns:
        dict: The bitrise build_params to specify. Empty dict if unspecified.
    """
    return task["payload"].get("build_params", {})
