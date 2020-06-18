# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Build the cached_task digest to prevent rerunning tasks if the code hasn't changed.
"""

from __future__ import absolute_import, print_function, unicode_literals

import hashlib
import json
import os
import subprocess

import taskgraph
from taskgraph.transforms.base import TransformSequence
from taskgraph.util.hash import hash_paths
from taskgraph.util.memoize import memoize

transforms = TransformSequence()

BASE_DIR = os.getcwd()

@transforms.add
def add_resources(config, tasks):
    for task in tasks:
        resources = task.pop("resources", None)
        if resources:
            task.setdefault("attributes", {})["resources"] = resources
        yield task


@transforms.add
def build_cache(config, tasks):
    for task in tasks:
        if task.get("cache", True) and not taskgraph.fast:
            digest_data = []
            digest_data.append(
                json.dumps(task.get("attributes", {}).get("digest-extra", {}), indent=2, sort_keys=True)
            )
            resources = task.get("attributes", {}).get("resources", [])
            for resource in resources:
                digest_data.append(hash_paths(os.path.join(BASE_DIR, resource), ['']))
            cache_name = task["name"].replace(":", "-")
            task["cache"] = {
                "type": "scriptworker-scripts.v1.{}".format(config.kind),
                "name": cache_name,
                "digest-data": digest_data,
            }

        yield task


@transforms.add
def set_label(config, jobs):
    """Set the job label, which the `cached_tasks` transform needs"""
    for job in jobs:
        job["label"] = "{}-{}".format(config.kind, job.pop("name"))
        yield job
