# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Create a task per job python-version
"""

from __future__ import absolute_import, print_function, unicode_literals
from copy import deepcopy

from taskgraph.transforms.base import TransformSequence


transforms = TransformSequence()

def _replace_string(obj, repl_dict):
    if isinstance(obj, dict):
        return {k: v.format(**repl_dict) for k, v in obj.items()}
    elif isinstance(obj, list):
        for c in range(0, len(obj)):
            obj[c] = obj[c].format(**repl_dict)
    else:
        obj = obj.format(**repl_dict)
    return obj


@transforms.add
def tasks_per_python_version(config, jobs):
    for job in jobs:
        for python_version in job.pop("python-versions"):
            task = deepcopy(job)
            repl_dict = {"name": job["name"], "python_version": python_version}
            task["label"] = _replace_string(task["label"], repl_dict)
            task['worker']['docker-image'] = _replace_string(task['worker']['docker-image'], repl_dict)
            task['description'] = _replace_string(task['description'], repl_dict)
            if task.get('run', {}).get('command'):
                task['run']['command'] = _replace_string(task['run']['command'], repl_dict)
            if task['worker'].get('command'):
                task['worker']['command'] = _replace_string(task['worker']['command'], repl_dict)
            if task.get('docker-repo'):
                task['docker-repo'] = _replace_string(task['docker-repo'], repl_dict)
            task.setdefault("attributes", {}).update({
                "script-name": job["name"],
                "python-version": python_version,
            })
            yield task


@transforms.add
def skip_on_project_specific_branches(config, jobs):
    """Skip if the branch is project-specific for a different project."""
    project_specific_prefixes = ("refs/heads/dev-", "refs/heads/production-")
    for job in jobs:
        script_name = job["attributes"]["script-name"]
        project_specific_branches = ["{}{}".format(prefix, script_name) for prefix in project_specific_prefixes]
        if config.params['head_ref'].startswith(project_specific_prefixes) and \
                config.params['head_ref'] not in project_specific_branches:
            continue
        yield job
