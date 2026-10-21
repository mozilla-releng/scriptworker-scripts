from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import AsyncMock

import pytest

from mozapkpublisher.common.schedule import ScheduledReleaseException
from mozapkpublisher.sgs_api import SamsungGalaxyStore
from mozapkpublisher.sgs_api.content_info import AppContentInfo

CONTENT_ID = "content-1"
PACKAGE_NAME = "org.mozilla.firefox"


class _FileDescriptor:
    """Minimal stand-in for the file object `upload_apks` expects (it only reads `.name`)."""

    def __init__(self, name):
        self.name = name


def _soon():
    return datetime.now(timezone.utc) + timedelta(days=7)


def _apk():
    return (_FileDescriptor("/tmp/fenix.apk"), {"package_name": PACKAGE_NAME, "architecture": "arm64-v8a", "version_name": "1.0"})


def _content_info():
    return AppContentInfo(
        {
            "contentId": CONTENT_ID,
            "contentStatus": "FOR_SALE",
            "defaultLanguageCode": "EN",
            "paid": "N",
            "publicationType": "03",
            "binaryList": [{"binarySeq": "1", "gms": "Y"}],
        }
    )


def _mock_store_api(sgs):
    """Stub every call `upload_apks` makes, so the test sees only what it was asked to send."""
    sgs.infer_content_id_from_package_name = AsyncMock(return_value=CONTENT_ID)
    sgs.upload_file = AsyncMock(return_value="file-key")
    sgs.api.get_content_info = AsyncMock(return_value=[_content_info()])
    sgs.api.update_content_info = AsyncMock()
    sgs.api.add_binary = AsyncMock(return_value={"data": {"binarySeq": "2"}})
    sgs.api.submit_app = AsyncMock()


@pytest.mark.asyncio
async def test_a_scheduled_release_sets_the_date_and_submits(responses_mock):
    when = _soon()
    async with SamsungGalaxyStore("service_account_id", "access_token") as sgs:
        _mock_store_api(sgs)
        await sgs.upload_apks(PACKAGE_NAME, [_apk()], None, submit=True, scheduled_release_date=when)

    assert sgs.api.update_content_info.call_args.kwargs["scheduled_release_date"] == when
    sgs.api.submit_app.assert_awaited_once_with(CONTENT_ID)


@pytest.mark.asyncio
async def test_an_unscheduled_release_is_left_for_manual_publication(responses_mock):
    async with SamsungGalaxyStore("service_account_id", "access_token") as sgs:
        _mock_store_api(sgs)
        await sgs.upload_apks(PACKAGE_NAME, [_apk()], None, submit=True)

    assert sgs.api.update_content_info.call_args.kwargs["scheduled_release_date"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("dry_run", (True, False))
async def test_a_schedule_without_submit_is_refused_before_contacting_the_store(responses_mock, dry_run):
    """Having the `responses_mock` fixture makes any real request fail the test."""
    async with SamsungGalaxyStore("service_account_id", "access_token", dry_run=dry_run) as sgs:
        with pytest.raises(ScheduledReleaseException, match="without `submit`"):
            await sgs.upload_apks(PACKAGE_NAME, [_apk()], None, submit=False, scheduled_release_date=_soon())


@pytest.mark.asyncio
async def test_a_date_that_goes_stale_during_the_upload_is_not_submitted(responses_mock):
    """The date is checked again right before `submit_app`, since uploading the binaries
    can outlast a date that was close when the task started."""
    when = datetime.now(timezone.utc) + timedelta(days=1)
    async with SamsungGalaxyStore("service_account_id", "access_token") as sgs:
        _mock_store_api(sgs)
        with mock.patch("mozapkpublisher.common.schedule.datetime") as schedule_datetime:
            schedule_datetime.now.side_effect = [when - timedelta(seconds=1), when + timedelta(seconds=1)]
            with pytest.raises(ScheduledReleaseException, match="has passed .*, so the update was left in Seller Portal"):
                await sgs.upload_apks(PACKAGE_NAME, [_apk()], None, submit=True, scheduled_release_date=when)

    sgs.api.add_binary.assert_awaited_once()
    sgs.api.submit_app.assert_not_awaited()
