from scriptworker_client.exceptions import TaskVerificationError
from scriptworker_client.utils import get_single_item_from_sequence


def extract_common_scope_prefix(config, task):
    prefixes = _get_allowed_scope_prefixes(config)
    scopes = task["scopes"]

    found_prefixes = set((prefix for prefix in prefixes for scope in scopes if scope.startswith(prefix)))

    return get_single_item_from_sequence(
        sequence=found_prefixes,
        condition=lambda _: True,
        ErrorClass=TaskVerificationError,
        no_item_error_message=f"No scope starting with any of these prefixes {prefixes} found",
        too_many_item_error_message="Too many prefixes found",
    )


def _get_allowed_scope_prefixes(config):
    prefixes = config["taskcluster_scope_prefixes"]
    return [prefix if prefix.endswith(":") else "{}:".format(prefix) for prefix in prefixes]


def get_action(task, prefix):
    action_prefix = f"{prefix}action:"
    return _extract_last_chunk_of_scope(task, action_prefix)


def get_github_project(task, prefix):
    project_prefix = f"{prefix}project:"
    return _extract_last_chunk_of_scope(task, project_prefix)


def _extract_last_chunk_of_scope(task, prefix):
    scope = get_single_item_from_sequence(
        sequence=task["scopes"],
        condition=lambda scope: scope.startswith(prefix),
        ErrorClass=TaskVerificationError,
        no_item_error_message=f'No scope starting with any of this prefix "{prefix}" found',
        too_many_item_error_message=f'Too many scopes with this prefix "{prefix}" found',
    )

    last_chunk = scope.split(":")[prefix.count(":") :]  # the chunk after the prefix is the product name
    return ":".join(last_chunk)


def check_action_is_allowed(project_config, action):
    if action not in project_config["allowed_actions"]:
        raise TaskVerificationError(f'Action "{action}" is not allowed for this project')
