"""
Scheduled releases for the async store clients (Samsung Galaxy Store, Huawei AppGallery
and the vivo app store). Each of them can submit a release that goes live at a given time
instead of as soon as it passes review. The checks every store shares live here; limits
only one store has (e.g. vivo's scheduling horizon) stay in that store's module.
"""

from datetime import datetime, timezone
from typing import Optional

from mozapkpublisher.common.exceptions import StoreException


class ScheduledReleaseException(StoreException):
    pass


def parse_scheduled_release_date(value: str) -> datetime:
    """
    Parse an ISO 8601 release date into an aware `datetime`.
    """
    try:
        # Upper-cased to match the task schema's RFC 3339 check, which accepts a
        # lowercase `t` separator and `z` offset that `fromisoformat` would reject.
        parsed = datetime.fromisoformat(value.upper())
    except AttributeError, TypeError, ValueError:
        raise ScheduledReleaseException(
            "Could not read {!r} as a scheduled release date. It has to be an ISO 8601 datetime with a UTC offset, for example '2026-10-01T09:00:00Z'.".format(
                value
            )
        ) from None

    if parsed.tzinfo is None:
        raise ScheduledReleaseException(
            "The scheduled release date {!r} has no UTC offset, so the time it means depends on "
            "where it is read. Give one, for example '2026-10-01T09:00:00Z'.".format(value)
        )

    return parsed


def check_can_schedule(
    package_name: str,
    scheduled_release_date: Optional[datetime],
    *,
    submit: bool,
    rollout_rate: Optional[int],
) -> None:
    """
    Enforce the rules pushapkscript applies to every scheduled release: it must be
    submitted, it must be a full release rather than a staged rollout, and it must be in
    the future.

    These are local checks, meant to run ahead of each store's `dry_run` bail-out so a
    task that can never be committed also fails on a dry run.
    """
    if scheduled_release_date is None:
        return

    if not submit:
        raise ScheduledReleaseException(
            "A scheduled release date ({}) was given for {} without `submit`. A schedule is only applied to a "
            "release that is submitted, so nothing was uploaded. Set `submit` to schedule it.".format(scheduled_release_date.isoformat(), package_name)
        )

    if rollout_rate is not None:
        raise ScheduledReleaseException(
            "A scheduled release date ({}) and a {}% rollout were both given for {}. Scheduling a staged "
            "rollout is not supported, so nothing was uploaded. Remove the rollout percentage to schedule a "
            "full release.".format(scheduled_release_date.isoformat(), rollout_rate, package_name)
        )

    check_not_passed(package_name, scheduled_release_date, consequence="nothing was uploaded")


def check_not_passed(name: str, scheduled_release_date: datetime, *, consequence: str) -> None:
    """
    Refuse a scheduled release date that is no longer in the future. Stores run this
    once before uploading and again right before submitting, since a large upload (and
    any submit retries) can outlast a date that was close when the task started.

    `consequence` says what state the release was left in, for the error message.
    """
    now = datetime.now(timezone.utc)
    if scheduled_release_date <= now:
        raise ScheduledReleaseException(
            "The scheduled release date {} for {} has passed (it is now {}), so {}. Re-run with a later date.".format(
                scheduled_release_date.isoformat(), name, now.isoformat(timespec="seconds"), consequence
            )
        )
