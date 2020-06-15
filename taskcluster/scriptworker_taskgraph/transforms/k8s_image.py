# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Kubernetes docker image builds.
"""

from __future__ import absolute_import, print_function, unicode_literals
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
            "HEAD_REV": config.params['head_rev'],
            "REPO_URL": config.params['head_repository'],
            "PROJECT_NAME": project_name,
            "TASKCLUSTER_ROOT_URL": "$TASKCLUSTER_ROOT_URL",
            "DOCKER_TAG": "unknown",
            "DOCKER_REPO": job.pop("docker-repo"),
        })
        force_push_docker_image = False
        if tasks_for == 'github-pull-request':
            env["DOCKER_TAG"] = "pull-request"
        elif tasks_for == 'github-push':
            for ref_name in ("dev", "production"):
                if config.params['head_ref'] == "refs/heads/{}-{}".format(ref_name, project_name):
                    env["DOCKER_TAG"] = ref_name
                    force_push_docker_image = True
                    break
            else:
                if config.params['head_ref'].startswith('refs/heads/'):
                    env["DOCKER_TAG"] = config.params['head_ref'].replace('refs/heads/', '')
        if env["DOCKER_TAG"] in ("production", "dev") and config.params["level"] == "3":
            env["SECRET_URL"] = secret_url
            env["PUSH_DOCKER_IMAGE"] = "1"
            env["DOCKERHUB_EMAIL"] = config.graph_config["docker"]["email"]
            env["DOCKERHUB_USER"] = config.graph_config["docker"]["user"]
            scopes.append('secrets:get:project/releng/scriptworker-scripts/deploy')
            if force_push_docker_image:
                attributes.setdefault("digest-extra", {}).setdefault("force_run", time.time())
        else:
            env["PUSH_DOCKER_IMAGE"] = "0"
        yield job
