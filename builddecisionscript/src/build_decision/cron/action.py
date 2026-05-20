# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json
import logging
import os

import taskcluster

from ..util.http import SESSION
from ..util.trigger_action import render_action

logger = logging.getLogger(__name__)


def find_decision_task(repository, revision):
    """Given the parameters for this action, find the taskId of the decision
    task"""
    index = taskcluster.Index(taskcluster.optionsFromEnvironment(), session=SESSION)
    decision_index = f"{repository.trust_domain}.v2.{repository.project}.revision.{revision}.taskgraph.decision"  # noqa
    logger.info("Looking for index: %s", decision_index)
    task_id = index.findTask(decision_index)["taskId"]
    logger.info("Found decision task: %s", task_id)
    return task_id


def run_trigger_action(job_name, job, *, repository, push_info, dry_run):
    action_name = job["action-name"]
    decision_task_id = find_decision_task(repository, push_info["revision"])

    action_input = {}

    if job.get("include-cron-input") and "HOOK_PAYLOAD" in os.environ:
        cron_hook_payload = json.loads(os.environ["HOOK_PAYLOAD"])
        logger.info(
            "Cron Hook Payload:\n%s",
            json.dumps(cron_hook_payload, indent=4, sort_keys=True),
        )
        action_input.update(cron_hook_payload)

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
