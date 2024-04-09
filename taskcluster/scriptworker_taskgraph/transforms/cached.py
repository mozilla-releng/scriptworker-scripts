# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Build the cached_task digest to prevent rerunning tasks if the code hasn't changed.
"""

import os

import taskgraph
from taskgraph.transforms.base import TransformSequence
from taskgraph.util.hash import hash_paths

transforms = TransformSequence()

BASE_DIR = os.getcwd()


@transforms.add
def add_resources(config, tasks):
    for task in tasks:
        resources = task.pop("resources", [])
        attributes = task.setdefault("attributes", {})
        if attributes.get("resources") is not None:
            if resources and attributes["resources"] != resources:
                raise Exception(
                    "setting {} {} task.attributes.resources to {}: it's already set to {}!".format(
                        config.kind,
                        task.get("name"),
                        resources,
                        attributes["resources"],
                    )
                )
        attributes["resources"] = resources
        yield task


@transforms.add
def build_cache(config, tasks):
    for task in tasks:
        if task.get("cache", True) and not taskgraph.fast:
            digest_data = []
            resources = task["attributes"]["resources"]
            for resource in resources:
                digest_data.append(hash_paths(os.path.join(BASE_DIR, resource), [""]))
            cache_name = task["name"].replace(":", "-")
            task["cache"] = {
                "type": f"scriptworker-scripts.v1.{config.kind}",
                "name": cache_name,
                "digest-data": digest_data,
            }

        yield task


@transforms.add
def set_label(config, tasks):
    """Set the task label, which the `cached_tasks` transform needs"""
    for task in tasks:
        task["label"] = "{}-{}".format(config.kind, task.pop("name"))
        yield task
