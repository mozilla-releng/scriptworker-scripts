from textwrap import dedent
from typing import Any

from scriptworker_client.exceptions import TaskVerificationError
from scriptworker_client.utils import get_single_item_from_sequence


def validate_scope_prefixes(config, task):
    """Validates scope prefixes.

    Args:
        config (dict): The bitrisescript config.
        task (dict): The task definition.
    """
    prefix = config["taskcluster_scope_prefix"]

    invalid_scopes = {s for s in task["scopes"] if not s.startswith(prefix)}
    if invalid_scopes:
        invalid_scopes = "\n".join(sorted(invalid_scopes))
        raise TaskVerificationError(
            dedent(
                f"""
            The following scopes have an invalid prefix:
            {invalid_scopes}

            Expected prefix:
            {prefix}
            """.lstrip()
            )
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
    prefix = config["taskcluster_scope_prefix"]
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
    prefix = config["taskcluster_scope_prefix"]
    workflow_prefix = f"{prefix}workflow:"
    return [_extract_last_chunk_of_scope(scope, workflow_prefix) for scope in task["scopes"] if scope.startswith(workflow_prefix)]


def get_build_params(task: dict[str, Any]) -> dict[str, Any]:
    """Get the build_params from the task payload or an empty dict.

    Args:
        task (dict): The task definition.

    Returns:
        dict: The bitrise build_params to specify. Empty dict if unspecified.
    """
    return task["payload"].get("build_params", {})
