from scriptworker_client import artifacts
from scriptworker_client.exceptions import TaskVerificationError


def get_msix_file_paths(config, task):
    artifacts_per_task_id, _ = artifacts.get_upstream_artifacts_full_paths_per_task_id(config, task)

    all_artifacts = [artifact for artifacts in artifacts_per_task_id.values() for artifact in artifacts]

    filtered_artifacts = [item for item in all_artifacts if item.endswith(".store.msix")]
    if len(filtered_artifacts) == 0:
        raise TaskVerificationError("No upstream artifact is a store msix")
    return filtered_artifacts
