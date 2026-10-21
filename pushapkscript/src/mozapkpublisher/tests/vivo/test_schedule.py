from datetime import datetime, timedelta, timezone

import pytest

from .common import recorded_calls, register_publish_flow
import mozapkpublisher.common.schedule as schedule
import mozapkpublisher.vivo_api as vivo_api
from mozapkpublisher.common.schedule import ScheduledReleaseException
from mozapkpublisher.vivo_api import (
    MAX_SCHEDULE_DAYS_AHEAD,
    METHOD_UPDATE_SUBMIT,
    ONLINE_TYPE_PUBLISH_NOW,
    ONLINE_TYPE_SCHEDULED,
    VivoAppStore,
    latest_schedulable_release_date,
)
from mozapkpublisher.vivo_api import VivoAppStoreApi
from mozapkpublisher.vivo_api.error import VivoUpdateException


class _clock_at:
    """A stand-in for the `datetime` module that freezes `now()` at a chosen instant."""

    def __init__(self, when):
        self._when = when

    def __getattr__(self, name):
        return getattr(datetime, name) if name != "now" else None

    def now(self, tz=None):
        return self._when

PACKAGE_NAME = "org.mozilla.firefox"
ACCESS_KEY = "k"
ACCESS_SECRET = "s"


def _soon():
    return datetime.now(timezone.utc) + timedelta(days=7)


@pytest.mark.parametrize(
    "now,expected",
    (
        pytest.param(datetime(2026, 9, 22, 10, 30, tzinfo=timezone.utc), "2026-09-30T23:59:00+00:00", id="midday"),
        # The bound is the end of the eighth day, not now plus 8*24h, so it does not move
        # with the time of day the task happens to run at.
        pytest.param(datetime(2026, 9, 22, 23, 59, 59, tzinfo=timezone.utc), "2026-09-30T23:59:00+00:00", id="just_before_midnight"),
        pytest.param(datetime(2026, 9, 23, 0, 0, 1, tzinfo=timezone.utc), "2026-10-01T23:59:00+00:00", id="just_after_midnight"),
    ),
)
def test_the_latest_schedulable_date_is_2359_on_the_eighth_day(now, expected):
    assert latest_schedulable_release_date(now).isoformat() == expected
    assert (latest_schedulable_release_date(now).date() - now.date()).days == MAX_SCHEDULE_DAYS_AHEAD


@pytest.mark.asyncio
async def test_a_date_at_the_limit_is_accepted(responses_mock, apk, monkeypatch):
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name)
    now = datetime(2026, 9, 22, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(vivo_api, "datetime", _clock_at(now))
    monkeypatch.setattr(schedule, "datetime", _clock_at(now))
    when = latest_schedulable_release_date(now)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True, scheduled_release_date=when)

    assert recorded_calls(responses_mock)[-1].kwargs["data"]["onlineTime"] == int(when.timestamp() * 1000)


@pytest.mark.asyncio
async def test_a_date_past_the_limit_is_refused_before_uploading(responses_mock, apk, monkeypatch):
    """One minute past the bound is refused, so the check is the bound itself rather than
    a rounded-off day count."""
    now = datetime(2026, 9, 22, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(vivo_api, "datetime", _clock_at(now))
    monkeypatch.setattr(schedule, "datetime", _clock_at(now))
    when = latest_schedulable_release_date(now) + timedelta(minutes=1)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(VivoUpdateException, match="further ahead than vivo accepts"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True, scheduled_release_date=when)

    assert recorded_calls(responses_mock) == []


@pytest.mark.asyncio
async def test_a_scheduled_release_submits_with_the_date(responses_mock, apk):
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name)
    when = _soon()

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True, scheduled_release_date=when)

    submit_call = recorded_calls(responses_mock)[-1].kwargs["data"]
    assert submit_call["method"] == METHOD_UPDATE_SUBMIT
    assert submit_call["onlineType"] == ONLINE_TYPE_SCHEDULED
    assert submit_call["onlineTime"] == int(when.timestamp() * 1000)


@pytest.mark.asyncio
async def test_no_date_still_publishes_as_soon_as_review_passes(responses_mock, apk):
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    submit_call = recorded_calls(responses_mock)[-1].kwargs["data"]
    assert submit_call["onlineType"] == ONLINE_TYPE_PUBLISH_NOW
    assert "onlineTime" not in submit_call


@pytest.mark.asyncio
async def test_a_date_without_submit_is_refused_before_uploading(responses_mock, apk):
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(ScheduledReleaseException, match="without `submit`"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=False, scheduled_release_date=_soon())

    assert recorded_calls(responses_mock) == []


@pytest.mark.asyncio
async def test_a_date_in_the_past_is_refused_before_uploading(responses_mock, apk):
    """Submitting a stale schedule publishes immediately."""
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(ScheduledReleaseException, match="has passed .*, so nothing was uploaded"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True, scheduled_release_date=datetime.now(timezone.utc) - timedelta(seconds=1))

    assert recorded_calls(responses_mock) == []


@pytest.mark.asyncio
async def test_a_date_that_goes_stale_during_the_upload_is_not_submitted(responses_mock, apk, monkeypatch):
    """The pre-upload guard cannot help here: a multi-hundred-megabyte upload sits between
    it and the submit, so the date is checked again against the clock at submit time."""
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name)
    when = datetime.now(timezone.utc) + timedelta(seconds=30)

    real_update_basic_info = VivoAppStoreApi.update_basic_info

    async def slow_upload(self, *args, **kwargs):
        # Stand in for the upload taking longer than the schedule had left.
        result = await real_update_basic_info(self, *args, **kwargs)
        monkeypatch.setattr(schedule, "datetime", _clock_at(when + timedelta(seconds=1)))
        return result

    monkeypatch.setattr(VivoAppStoreApi, "update_basic_info", slow_upload)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(ScheduledReleaseException, match="has passed .*, so the APK was left uploaded and bound but NOT submitted"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True, scheduled_release_date=when)

    # Uploaded and bound, but never submitted.
    assert len(recorded_calls(responses_mock)) == 3


@pytest.mark.asyncio
async def test_a_scheduled_dry_run_still_refuses_an_impossible_request(responses_mock, apk):
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET, dry_run=True) as vivo:
        with pytest.raises(ScheduledReleaseException, match="without `submit`"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=False, scheduled_release_date=_soon())
