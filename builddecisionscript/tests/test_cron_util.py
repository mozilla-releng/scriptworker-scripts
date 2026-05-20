import datetime
import os

import pytest
import taskcluster

import build_decision.cron.util as util

UTCNOW = datetime.datetime(2022, 4, 14, 20, 45, 50, 123345)
CREATED_STR = "2022-04-14T19:08:37.357Z"
CREATED = datetime.datetime.strptime(CREATED_STR, "%Y-%m-%dT%H:%M:%S.%fZ")


@pytest.mark.parametrize(
    "time, sched, expected, raises",
    (
        (
            # Raise on a minute that isn't a multiple of 15
            None,
            {"minute": 17},
            None,
            Exception,
        ),
        (
            # We match minute, nothing else specified!
            UTCNOW,
            {"minute": 45},
            True,
            False,
        ),
        (
            # We don't match minute, nothing else specified!
            UTCNOW,
            {"minute": 30},
            False,
            False,
        ),
        (
            # We don't match hour
            UTCNOW,
            {"hour": 17, "minute": 45},
            False,
            False,
        ),
        (
            # We don't match day
            UTCNOW,
            {"day": 10},
            False,
            False,
        ),
        (
            # We don't match weekday
            UTCNOW,
            {"weekday": "wednesday"},
            False,
            False,
        ),
        (
            # Weekday isn't a string
            UTCNOW,
            {"weekday": {"one": "two"}},
            False,
            False,
        ),
        (
            # Everything matches
            UTCNOW,
            {"weekday": "thursday", "day": 14, "hour": 20, "minute": 45},
            True,
            False,
        ),
    ),
)
def test_match_utc(time, sched, expected, raises):
    """Add coverage for cron.util.match_utc."""
    if raises:
        with pytest.raises(raises):
            util.match_utc(time=time, sched=sched)
    else:
        assert util.match_utc(time=time, sched=sched) == expected


@pytest.mark.parametrize(
    "env, expected",
    (
        (
            # No TASK_ID, no CRON_TIME: fall back to UTCNOW
            {},
            datetime.datetime(2022, 4, 14, 20, 45, 0, 0),
        ),
        (
            # No TASK_ID, but there is CRON_TIME: use CRON_TIME
            {"CRON_TIME": "1649994160"},
            datetime.datetime(2022, 4, 15, 3, 30, 0, 0),
        ),
        (
            # TASK_ID: use CREATED
            {"TASK_ID": "task_id"},
            datetime.datetime(2022, 4, 14, 19, 0, 0, 0),
        ),
    ),
)
def test_calculate_time(mocker, env, expected):
    """Add coverage for cron.util.calculate_time."""
    fake_queue = mocker.MagicMock()
    fake_task = {"created": CREATED_STR}
    fake_queue.task.return_value = fake_task
    env.setdefault("TASKCLUSTER_PROXY_URL", "http://taskcluster")

    class fake_datetime(datetime.datetime):
        def utcnow():
            return UTCNOW

    mocker.patch.object(os, "environ", new=env)
    mocker.patch.object(datetime, "datetime", new=fake_datetime)
    mocker.patch.object(taskcluster, "Queue", return_value=fake_queue)

    assert util.calculate_time() == expected
