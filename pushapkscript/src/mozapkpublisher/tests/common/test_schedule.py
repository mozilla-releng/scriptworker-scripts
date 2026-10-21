from datetime import datetime, timedelta, timezone

import pytest

from mozapkpublisher.common.schedule import ScheduledReleaseException, check_can_schedule, check_not_passed, parse_scheduled_release_date

A_DATE = "2026-10-01T09:00:00Z"
A_DATE_MS = 1790845200000
PACKAGE_NAME = "org.mozilla.firefox"


def _soon():
    return datetime.now(timezone.utc) + timedelta(days=7)


@pytest.mark.parametrize(
    "value,expected_ms",
    (
        pytest.param(A_DATE, A_DATE_MS, id="zulu"),
        pytest.param("2026-10-01T09:00:00+00:00", A_DATE_MS, id="explicit_utc"),
        pytest.param("2026-10-01T17:00:00+08:00", A_DATE_MS, id="other_offset"),
        pytest.param("2026-10-01T09:00:00.000Z", A_DATE_MS, id="milliseconds"),
    ),
)
def test_a_release_date_parses_to_the_instant_it_names(value, expected_ms):
    parsed = parse_scheduled_release_date(value)

    assert int(parsed.timestamp() * 1000) == expected_ms


@pytest.mark.parametrize("value", ("2026-10-01t09:00:00z", "2026-10-01T09:00:00z", "2026-10-01t09:00:00Z"))
def test_a_lowercase_rfc_3339_release_date_is_accepted(value):
    """The task schema's `date-time` check is case-insensitive on the `t` separator and
    the `z` offset, so refusing them here would fail a payload the schema let through --
    after the APKs had already been downloaded."""
    assert int(parse_scheduled_release_date(value).timestamp() * 1000) == A_DATE_MS


def test_a_release_date_without_an_offset_is_refused():
    with pytest.raises(ScheduledReleaseException, match="no UTC offset"):
        parse_scheduled_release_date("2026-10-01T09:00:00")


@pytest.mark.parametrize("value", ("", "tomorrow", "2026-13-45T99:00:00Z", None))
def test_an_unreadable_release_date_is_refused(value):
    with pytest.raises(ScheduledReleaseException, match="ISO 8601"):
        parse_scheduled_release_date(value)


@pytest.mark.parametrize("submit", (True, False))
def test_no_schedule_is_always_accepted(submit):
    check_can_schedule(PACKAGE_NAME, None, submit=submit, rollout_rate=10)


def test_a_future_schedule_with_submit_is_accepted():
    check_can_schedule(PACKAGE_NAME, _soon(), submit=True, rollout_rate=None)


def test_a_schedule_without_submit_is_refused():
    with pytest.raises(ScheduledReleaseException, match="without `submit`"):
        check_can_schedule(PACKAGE_NAME, _soon(), submit=False, rollout_rate=None)


def test_a_schedule_with_a_rollout_is_refused():
    with pytest.raises(ScheduledReleaseException, match="10% rollout"):
        check_can_schedule(PACKAGE_NAME, _soon(), submit=True, rollout_rate=10)


def test_a_schedule_in_the_past_is_refused():
    with pytest.raises(ScheduledReleaseException, match="has passed .*, so nothing was uploaded"):
        check_can_schedule(PACKAGE_NAME, datetime.now(timezone.utc) - timedelta(seconds=1), submit=True, rollout_rate=None)


def test_check_not_passed_accepts_a_future_date():
    check_not_passed(PACKAGE_NAME, _soon(), consequence="unused")


def test_check_not_passed_reports_what_was_left_behind():
    with pytest.raises(ScheduledReleaseException, match="has passed .*, so the binary was NOT submitted. Re-run with a later date."):
        check_not_passed(PACKAGE_NAME, datetime.now(timezone.utc) - timedelta(seconds=1), consequence="the binary was NOT submitted")
