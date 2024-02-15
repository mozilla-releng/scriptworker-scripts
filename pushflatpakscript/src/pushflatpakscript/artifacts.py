from scriptworker import artifacts
from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

from taskcluster import Queue


def get_flatpak_file_path(context):
    artifacts_per_task_id, _ = artifacts.get_upstream_artifacts_full_paths_per_task_id(context)

    all_artifacts = [artifact for artifacts in artifacts_per_task_id.values() for artifact in artifacts]

    return get_single_item_from_sequence(
        all_artifacts,
        condition=lambda artifact: artifact.endswith(".flatpak.tar.xz"),
        ErrorClass=TaskVerificationError,
        no_item_error_message="No upstream artifact is a tar.xz",
        too_many_item_error_message="Too many flatpaks detected",
    )


def get_flatpak_build_log_url(context):
    upstream_artifacts = context.task["payload"]["upstreamArtifacts"]
    task_ids_and_relative_paths = ((artifact_definition["taskId"], artifact_definition["paths"]) for artifact_definition in upstream_artifacts)
    task_id, paths = get_single_item_from_sequence(
        task_ids_and_relative_paths, lambda t: any(p.endswith(".flatpak.tar.xz") for p in t[1]), ErrorClass=TaskVerificationError
    )
    queue = Queue(options={"rootUrl": context.config["taskcluster_root_url"]})
    return queue.buildUrl("getLatestArtifact", task_id, "public/logs/live_backing.log")
