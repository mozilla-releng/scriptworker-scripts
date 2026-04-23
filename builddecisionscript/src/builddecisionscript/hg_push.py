# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import time
from contextlib import contextmanager

from .decision import render_tc_yml

logger = logging.getLogger(__name__)


@contextmanager
def timed(description):
    start = time.perf_counter()
    yield
    logging.info(f"{description} took: {time.perf_counter() - start:.1f}")


# Allow triggering on-push task for pushes up to 3 days old.
MAX_TIME_DRIFT = 3 * 24 * 60 * 60


def get_revision_from_pulse_message(pulse_message):
    logger.info("Pulse Message:\n%s", pulse_message)

    pulse_payload = pulse_message["payload"]
    if pulse_payload["type"] != "changegroup.1":
        logger.info("Not a changegroup.1 message")
        return None

    push_count = len(pulse_payload["data"]["pushlog_pushes"])
    if push_count != 1:
        logger.info("Message has %d pushes; only one supported", push_count)
        return None

    head_count = len(pulse_payload["data"]["heads"])
    if head_count != 1:
        logger.info("Message has %d heads; only one supported", head_count)
        return None

    return pulse_payload["data"]["heads"][0]


def build_decision(*, repository, taskcluster_yml_repo, pulse_message, dry_run):
    logging.info("Running build-decision hg-push task")
    revision = get_revision_from_pulse_message(pulse_message)

    with timed("Fetching push info"):
        push = repository.get_push_info(revision=revision)

    if time.time() - push["pushdate"] > MAX_TIME_DRIFT:
        logger.warning("Push is too old, not triggering tasks")
        return

    with timed("Fetching .taskcluster.yml"):
        if taskcluster_yml_repo is None:
            taskcluster_yml = repository.get_file(".taskcluster.yml", revision=revision)
        else:
            taskcluster_yml = taskcluster_yml_repo.get_file(".taskcluster.yml")

    with timed("Rendering task"):
        task = render_tc_yml(
            taskcluster_yml,
            taskcluster_root_url=os.environ["TASKCLUSTER_ROOT_URL"],
            tasks_for="hg-push",
            push=push,
            repository=repository.to_json(),
        )

    task.display()
    if not dry_run:
        task.submit()
