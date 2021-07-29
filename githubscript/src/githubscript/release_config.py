import logging
import os
from mimetypes import guess_type

from scriptworker_client.exceptions import TaskVerificationError
from scriptworker_client.utils import get_artifact_path, get_single_item_from_sequence

log = logging.getLogger(__name__)


def get_release_config(product_config, task_payload, config):
    # support repo override for xpi-manifest, but support original workflow for fenix
    if product_config.get("allow_github_repo_override", False):
        if not task_payload.get("githubOwner", ""):
            raise TaskVerificationError("missing githubOwner from task")
        if not task_payload.get("githubRepoName", ""):
            raise TaskVerificationError("missing githubRepoName from task")

        owner = task_payload["githubOwner"]
        repo_name = task_payload["githubRepoName"]
        config_owner = product_config.get("github_owner", "")
        config_repo = product_config.get("github_repo_name", "")
        scope = product_config.get("scope_project", "")
        if scope:
            if config_owner != owner:
                raise TaskVerificationError(f'invalid owner "{owner}"" not found in config "{config_owner}" for scope "{scope}"')
            if product_config.get("github_repo_name", "") != repo_name:
                raise TaskVerificationError(f'invalid repo_name {repo_name} not found in config "{config_repo}" for scope "{scope}"')
    else:
        if not product_config.get("github_owner", ""):
            raise TaskVerificationError("missing github_owner from config")
        if not product_config.get("github_repo_name", ""):
            raise TaskVerificationError("missing github_repo_name from config")

        owner = product_config["github_owner"]
        repo_name = product_config["github_repo_name"]

    return {
        "artifacts": _get_artifacts(task_payload, config),
        "contact_github": product_config["contact_github"],
        "git_revision": task_payload["gitRevision"],
        "git_tag": task_payload["gitTag"],
        "github_owner": owner,
        "github_repo_name": repo_name,
        "github_token": product_config["github_token"],
        "is_prerelease": task_payload["isPrerelease"],
        "release_name": task_payload["releaseName"],
    }


def _get_artifacts(task_payload, config):
    artifacts = []

    for upstream_artifact_definition in task_payload["upstreamArtifacts"]:
        task_id = upstream_artifact_definition["taskId"]
        for taskcluster_path in upstream_artifact_definition["paths"]:
            local_path = get_artifact_path(task_id, taskcluster_path, work_dir=config["work_dir"])
            target_path = _find_target_path(taskcluster_path, task_payload["artifactMap"])

            artifacts.append({"content_type": guess_type(local_path)[0], "local_path": local_path, "name": target_path, "size": os.path.getsize(local_path)})

    return artifacts


def _find_target_path(taskcluster_path, artifact_map):
    target_path = None
    for map_ in artifact_map:
        if taskcluster_path in map_["paths"]:
            destinations = map_["paths"][taskcluster_path]["destinations"]
            candidate_destination = get_single_item_from_sequence(
                sequence=destinations,
                condition=lambda _: True,
                ErrorClass=TaskVerificationError,
                no_item_error_message=f'Path "{taskcluster_path}" has no destination defined',
                too_many_item_error_message=f'Path "{taskcluster_path}" has too many destinations',
            )

            if target_path is not None:
                raise TaskVerificationError(
                    f'Path "{taskcluster_path}" was already defined elsewhere in `artifactMap`. '
                    "Previous value: {target_path}. New value: {candidate_destination}"
                )

            target_path = candidate_destination

    if target_path is None:
        raise TaskVerificationError(f'Path "{taskcluster_path}" is not present in artifactMap')

    return target_path
