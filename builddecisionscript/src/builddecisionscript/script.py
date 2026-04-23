# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os

from scriptworker_client.client import sync_main

from .repository import Repository
from .secrets import get_secret
from .task import validate_task_schema

logger = logging.getLogger(__name__)


def _build_repository(payload):
    github_token = None
    if payload.get("githubTokenSecret"):
        github_token = get_secret(payload["githubTokenSecret"], secret_key="token")

    return Repository(
        repo_url=payload["repoUrl"],
        repository_type=payload["repositoryType"],
        project=payload["project"],
        level=payload["level"],
        trust_domain=payload["trustDomain"],
        github_token=github_token,
    )


async def async_main(config, task):
    validate_task_schema(task)
    payload = task["payload"]
    command = payload["command"]
    dry_run = payload.get("dryRun", False)

    repository = _build_repository(payload)

    if command == "hg-push":
        from .hg_push import build_decision  # noqa: PLC0415

        taskcluster_yml_repo = None
        if payload.get("taskclusterYmlRepo"):
            taskcluster_yml_repo = Repository(
                repo_url=payload["taskclusterYmlRepo"],
                repository_type="hg",
            )

        pulse_message = payload.get("pulseMessage")
        if pulse_message is None:
            raise ValueError("pulseMessage is required for hg-push command")

        build_decision(
            repository=repository,
            taskcluster_yml_repo=taskcluster_yml_repo,
            pulse_message=pulse_message,
            dry_run=dry_run,
        )

    elif command == "cron":
        from .cron import run  # noqa: PLC0415

        run(
            repository=repository,
            branch=payload.get("branch"),
            force_run=payload.get("forceRun"),
            cron_input=payload.get("cronInput"),
            dry_run=dry_run,
        )


def get_default_config(base_dir=None):
    base_dir = base_dir or os.path.dirname(os.getcwd())
    return {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "builddecisionscript_task_schema.json"),
    }


def main():
    return sync_main(async_main, default_config=get_default_config())


if __name__ == "__main__":
    main()
