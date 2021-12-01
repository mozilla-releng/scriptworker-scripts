"""Scriptworker-client artifact-related operations."""
import logging
import os
from pathlib import Path

from scriptworker_client.exceptions import TaskVerificationError
from scriptworker_client.utils import add_enumerable_item_to_dict

log = logging.getLogger(__name__)


def get_upstream_artifacts_full_paths_per_task_id(config, task):
    """List the downloaded upstream artifacts.

    Args:
        config (dict): the running config
        task (dict): the running task

    Returns:
        dict, dict: lists of the paths to upstream artifacts, sorted by task_id.
            First dict represents the existing upstream artifacts. The second one
            maps the optional artifacts that couldn't be downloaded

    Raises:
        scriptworker_client.exceptions.TaskVerificationError: when an artifact doesn't exist.

    """
    upstream_artifacts = task["payload"]["upstreamArtifacts"]
    task_ids_and_relative_paths = [
        (artifact_definition["taskId"], artifact_definition["paths"])
        for artifact_definition in upstream_artifacts
    ]

    optional_artifacts_per_task_id = get_optional_artifacts_per_task_id(
        upstream_artifacts
    )

    upstream_artifacts_full_paths_per_task_id = {}
    failed_paths_per_task_id = {}
    for task_id, paths in task_ids_and_relative_paths:
        for path in paths:
            try:
                path_to_add = get_and_check_single_upstream_artifact_full_path(
                    config, task_id, path
                )
                add_enumerable_item_to_dict(
                    dict_=upstream_artifacts_full_paths_per_task_id,
                    key=task_id,
                    item=path_to_add,
                )
            except TaskVerificationError:
                if path in optional_artifacts_per_task_id.get(task_id, []):
                    log.warning(
                        'Optional artifact "{}" of task "{}" not found'.format(
                            path, task_id
                        )
                    )
                    add_enumerable_item_to_dict(
                        dict_=failed_paths_per_task_id, key=task_id, item=path
                    )
                else:
                    raise

    return upstream_artifacts_full_paths_per_task_id, failed_paths_per_task_id


def get_and_check_single_upstream_artifact_full_path(config, task_id, path):
    """Return the full path where an upstream artifact is located on disk.

    Args:
        config (dict): the running config
        task_id (str): the task id of the task that published the artifact
        path (str): the relative path of the artifact

    Returns:
        str: absolute path to the artifact

    Raises:
        scriptworker_client.exceptions.TaskVerificationError: when an artifact doesn't exist.

    """
    abs_path = get_single_upstream_artifact_full_path(config, task_id, path)
    if not os.path.exists(abs_path):
        raise TaskVerificationError(
            "upstream artifact with path: {}, does not exist".format(abs_path)
        )

    return abs_path


def get_single_upstream_artifact_full_path(config, task_id, path):
    """Return the full path where an upstream artifact should be located.

    Artifact may not exist. If you want to be sure if does, use
    ``get_and_check_single_upstream_artifact_full_path()`` instead.

    This function is mainly used to move artifacts to the expected location.

    Args:
        config (dict): the running config
        task_id (str): the task id of the task that published the artifact
        path (str): the relative path of the artifact

    Returns:
        str: absolute path to the artifact should be.

    """
    parent_dir = os.path.abspath(os.path.join(config["work_dir"], "cot", task_id))
    full_path = os.path.join(parent_dir, path)
    assert_is_parent(full_path, parent_dir)
    return full_path


def get_optional_artifacts_per_task_id(upstream_artifacts):
    """Return every optional artifact defined in ``upstream_artifacts``, ordered by taskId.

    Args:
        upstream_artifacts: the list of upstream artifact definitions

    Returns:
        dict: list of paths to downloaded artifacts ordered by taskId

    """
    # A given taskId might be defined many times in upstreamArtifacts. Thus, we can't
    # use a dict comprehension
    optional_artifacts_per_task_id = {}

    for artifact_definition in upstream_artifacts:
        if artifact_definition.get("optional", False) is True:
            task_id = artifact_definition["taskId"]
            artifacts_paths = artifact_definition["paths"]

            add_enumerable_item_to_dict(
                dict_=optional_artifacts_per_task_id, key=task_id, item=artifacts_paths
            )

    return optional_artifacts_per_task_id


def assert_is_parent(path, parent_dir):
    """Raise ``TaskVerificationError`` if ``path`` is not under ``parent_dir``.

    Args:
        path (str): the path to inspect.
        parent_dir (str): the path that ``path`` should be under.

    Raises:
        TaskVerificationError: if ``path`` is not under ``parent_dir``.

    """
    p1 = Path(os.path.realpath(path))
    p2 = Path(os.path.realpath(parent_dir))
    if p1 != p2 and p2 not in p1.parents:
        raise TaskVerificationError("{} is not under {}!".format(p1, p2))
