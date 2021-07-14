# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Kubernetes docker image builds.
"""

from copy import deepcopy
import time

from taskgraph.transforms.base import TransformSequence


transforms = TransformSequence()


@transforms.add
def add_dependencies(config, jobs):
    """Add dependencies that match python-version and script-name.

    Also copy the resources attribute, and fail if there are unexpected
    discrepancies in upstream deps.

    """
    for job in jobs:
        attributes = job["attributes"]
        dependencies = job.setdefault("dependencies", {})
        resources = None
        for dep_task in config.kind_dependencies_tasks:
            dep_attrs = dep_task.attributes
            dep_kind = dep_task.kind
            if dep_attrs["python-version"]  == attributes["python-version"] and \
                    dep_attrs["script-name"] == attributes["script-name"]:
                if dependencies.get(dep_kind):
                    raise Exception("Duplicate kind {kind} dependencies: {existing_label}, {new_label}".format(
                        kind=dep_kind,
                        existing_label=dependencies[dep_kind]["label"],
                        new_label=dep_task.label,
                    ))
                dependencies[dep_kind] = dep_task.label
                if dep_attrs.get("resources"):
                    if resources and resources != dep_attrs["resources"]:
                        raise Exception("Conflicting resources: {existing_digest} {new_digest}".format(
                            existing_digest=resources,
                            new_digest=dep_attrs["resources"],
                        ))
                    resources = dep_attrs["resources"]
        if resources:
            attributes["resources"] = resources
        yield job


@transforms.add
def set_environment(config, jobs):
    """Set the environment variables for the docker hub task."""
    for job in jobs:
        project_name = job["attributes"]["script-name"]
        secret_url = job.pop("deploy-secret-url")
        tasks_for = config.params['tasks_for']
        scopes = job.setdefault("scopes", [])
        attributes = job["attributes"]
        env = job["worker"].setdefault("env", {})
        env.update({
            "SCRIPTWORKER_HEAD_REV": config.params['head_rev'],
            "DOCKER_REPO": job.pop("docker-repo"),
            "DOCKER_TAG": config.params.get('docker_tag', 'unknown'),
            "PROJECT_NAME": project_name,
            "SCRIPTWORKER_HEAD_REPOSITORY": config.params['head_repository'],
            "TASKCLUSTER_ROOT_URL": "$TASKCLUSTER_ROOT_URL",
        })
        push_docker_image = config.params.get("push_docker_image")
        if push_docker_image:
            env.update({
                "SECRET_URL": secret_url,
                "PUSH_DOCKER_IMAGE": "1",
                "DOCKERHUB_EMAIL": config.graph_config["docker"]["email"],
                "DOCKERHUB_USER": config.graph_config["docker"]["user"],
            })
            scopes.append('secrets:get:project/releng/scriptworker-scripts/deploy')
        else:
            env["PUSH_DOCKER_IMAGE"] = "0"
        yield job
