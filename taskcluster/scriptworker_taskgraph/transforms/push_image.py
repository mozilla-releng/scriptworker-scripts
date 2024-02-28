# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Push-image transforms
"""

from datetime import datetime

from taskgraph.transforms.base import TransformSequence

transforms = TransformSequence()


@transforms.add
def set_task_requirements(config, tasks):
    """Set dynamic task requirements"""
    for task in tasks:
        name = task["name"]
        # dependencies
        task.setdefault("dependencies", {}).update({"image": f"build-docker-image-{name}"})
        task["run-on-git-branches"].extend((f"^dev\-{name}$", f"^production\-{name}$"))
        yield task


@transforms.add
def set_environment(config, tasks):
    """Set the environment variables for the docker hub task."""
    for task in tasks:
        scopes = task.setdefault("scopes", [])
        env = task["worker"].setdefault("env", {})
        head_rev = config.params["head_rev"]
        docker_repo = f"mozilla/releng-{task['name']}"
        docker_tag = config.params.get("docker_tag") or "unknown"
        date = datetime.now().strftime("%Y%m%d%H%M%S")
        docker_archive_tag = f"{docker_tag}-{date}-{head_rev}"
        env.update(
            {
                "APP": task["name"],
                "VCS_HEAD_REV": head_rev,
                "DOCKER_REPO": docker_repo,
                "DOCKER_TAG": docker_tag,
                "DOCKER_ARCHIVE_TAG": docker_archive_tag,
            }
        )
        push_docker_image = config.params.get("push_docker_image")
        if push_docker_image:
            env.update({"PUSH_DOCKER_IMAGE": "1"})
            scopes.append("secrets:get:project/releng/scriptworker-scripts/deploy")
        else:
            env["PUSH_DOCKER_IMAGE"] = "0"
        yield task
