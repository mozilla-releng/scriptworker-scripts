# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

import taskcluster

from ..util.http import SESSION
from ..util.trigger_action import render_action

logger = logging.getLogger(__name__)


def find_decision_task(repository, revision):
    """Given repository and revision, find the taskId of the decision task."""
    index = taskcluster.Index(taskcluster.optionsFromEnvironment(), session=SESSION)
    decision_index = f"{repository.trust_domain}.v2.{repository.project}.revision.{revision}.taskgraph.decision"
    logger.info("Looking for index: %s", decision_index)
    task_id = index.findTask(decision_index)["taskId"]
    logger.info("Found decision task: %s", task_id)
    return task_id


def run_trigger_action(job_name, job, *, repository, push_info, cron_input=None, dry_run):
    action_name = job["action-name"]
    decision_task_id = find_decision_task(repository, push_info["revision"])

    action_input = {}

    if job.get("include-cron-input") and cron_input:
        action_input.update(cron_input)

    if job.get("extra-input"):
        action_input.update(job["extra-input"])

    hook = render_action(
        action_name=action_name,
        task_id=None,
        decision_task_id=decision_task_id,
        action_input=action_input,
    )

    hook.display()
    if not dry_run:
        hook.submit()
