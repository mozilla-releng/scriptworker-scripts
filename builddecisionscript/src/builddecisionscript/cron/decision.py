# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import logging
import os
import shlex

from ..decision import render_tc_yml

logger = logging.getLogger(__name__)


def make_arguments(job):
    arguments = []
    if "target-tasks-method" in job:
        arguments.append("--target-tasks-method={}".format(job["target-tasks-method"]))
    if job.get("optimize-target-tasks") is not None:
        arguments.append(
            "--optimize-target-tasks={}".format(
                str(job["optimize-target-tasks"]).lower(),
            )
        )
    if "include-push-tasks" in job:
        arguments.append("--include-push-tasks")
    if "rebuild-kinds" in job:
        for kind in job["rebuild-kinds"]:
            arguments.append(f"--rebuild-kind={kind}")
    return arguments


def run_decision_task(job_name, job, *, repository, push_info, cron_input=None, dry_run):
    """Generate a basic decision task, based on the root .taskcluster.yml"""
    push_info = copy.deepcopy(push_info)
    push_info["owner"] = "cron"

    taskcluster_yml = repository.get_file(".taskcluster.yml", revision=push_info["revision"])

    arguments = make_arguments(job)

    effective_cron_input = {}
    if job.get("include-cron-input") and cron_input:
        effective_cron_input.update(cron_input)

    cron_info = {
        "task_id": os.environ.get("TASK_ID", "<cron task id>"),
        "job_name": job_name,
        "job_symbol": job["treeherder-symbol"],
        # args are shell-quoted since they are given to `bash -c`
        "quoted_args": " ".join(shlex.quote(a) for a in arguments),
        "input": effective_cron_input,
    }

    task = render_tc_yml(
        taskcluster_yml,
        taskcluster_root_url=os.environ["TASKCLUSTER_ROOT_URL"],
        tasks_for="cron",
        repository=repository.to_json(),
        push=push_info,
        cron=cron_info,
    )

    task.display()
    if not dry_run:
        task.submit()
