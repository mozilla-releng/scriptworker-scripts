# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import os

import attr
import jsone
import slugid
import taskcluster

from .util.http import SESSION

logger = logging.getLogger(__name__)


def render_tc_yml(tc_yml, **context):
    """
    Render .taskcluster.yml into an array of tasks.  This provides a context
    that is similar to that provided by actions and crons, but with `tasks-for`
    set to `hg-push`.
    """
    ownTaskId = slugid.nice()
    context["ownTaskId"] = ownTaskId
    rendered = jsone.render(tc_yml, context)

    task_count = len(rendered["tasks"])
    if task_count != 1:
        logger.critical(f"Rendered result has {task_count} tasks; only one supported")
        raise Exception()

    [task] = rendered["tasks"]
    task_id = task.pop("taskId")
    return Task(task_id, task)


@attr.s(frozen=True)
class Task:
    task_id = attr.ib()
    task_payload = attr.ib()

    def display(self):
        logger.info(
            "Decision Task:\n%s",
            json.dumps(self.task_payload, indent=4, sort_keys=True),
        )

    def submit(self):
        logger.info("Task Id: %s", self.task_id)

        if "TASKCLUSTER_PROXY_URL" in os.environ:
            queue = taskcluster.Queue(
                {"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]},
                session=SESSION,
            )
        else:
            queue = taskcluster.Queue(
                taskcluster.optionsFromEnvironment(), session=SESSION
            )
        queue.createTask(self.task_id, self.task_payload)
