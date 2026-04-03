# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging
import os

import taskcluster

from ..util.http import SESSION

logger = logging.getLogger(__name__)


def match_utc(*, time, sched):
    """Return True if time matches the given schedule.

    If minute is not specified, then every multiple of fifteen minutes will match.
    Times not an even multiple of fifteen minutes will result in an exception
    (since they would never run).
    If hour is not specified, any hour will match. Similar for day and weekday.
    """
    if sched.get("minute") and sched.get("minute") % 15 != 0:
        raise Exception("cron jobs only run on multiples of 15 minutes past the hour")

    if sched.get("minute") is not None and sched.get("minute") != time.minute:
        return False

    if sched.get("hour") is not None and sched.get("hour") != time.hour:
        return False

    if sched.get("day") is not None and sched.get("day") != time.day:
        return False

    if isinstance(sched.get("weekday"), str):
        if sched.get("weekday", "").lower() != time.strftime("%A").lower():
            return False
    elif sched.get("weekday") is not None:
        return False

    return True


def calculate_time():
    if "TASK_ID" not in os.environ:
        # running in a development environment, so look for CRON_TIME or use
        # the current time
        if "CRON_TIME" in os.environ:
            logger.warning("setting time based on $CRON_TIME")
            time = datetime.datetime.utcfromtimestamp(int(os.environ["CRON_TIME"]))
            logger.info("cron time: %s", time)
        else:
            logger.warning("using current time for time; try setting $CRON_TIME to a timestamp")
            time = datetime.datetime.utcnow()
    else:
        queue = taskcluster.Queue({"rootUrl": os.environ["TASKCLUSTER_PROXY_URL"]}, session=SESSION)
        task = queue.task(os.environ["TASK_ID"])
        created = task["created"]
        time = datetime.datetime.strptime(created, "%Y-%m-%dT%H:%M:%S.%fZ")

    # round down to the nearest 15m
    minute = time.minute - (time.minute % 15)
    time = time.replace(minute=minute, second=0, microsecond=0)
    logger.info(f"calculated cron schedule time is {time}")
    return time
