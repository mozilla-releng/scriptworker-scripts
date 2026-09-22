import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp

from mozapkpublisher.common.store_api import build_apk_file_name, request
from mozapkpublisher.common.utils import file_md5sum

from .auth import build_signed_params
from .content_info import AppContentInfo
from .error import VivoUpdateException, VivoUploadException
from .utils import raise_for_response_code, raise_for_status_with_message, response_data

BASE_URL = "https://developer-api.vivo.com/"

# Every interface is a POST to this single gateway route; the `method` parameter selects
# which one is being called.
ROUTER_ROUTE = "/router/rest"

logger = logging.getLogger(__name__)

# `onlineType` values accepted by `app.update.submit`. ONLINE_TYPE_SCHEDULED additionally
# requires an `onlineTime` timestamp.
ONLINE_TYPE_PUBLISH_NOW = 1
ONLINE_TYPE_SCHEDULED = 2

# The furthest ahead a release can be scheduled: 23:59 on the eighth day from today.
# This is observed in the vivo Developers console, which will not offer a later date --
# the published API documentation states no limit, so `app.update.submit` may well
# accept one and reject it later, or not enforce it at all.
MAX_SCHEDULE_DAYS_AHEAD = 8

# An APK upload can carry hundreds of megabytes, and `ClientSession` defaults to a timeout
# `total=300`, which fails any ongoing uploads. Dropping the timeout lets a slow link finish.
# `sock_connect=30` gives up if the connection takes more than 30 seconds to establish.
# `sock_read=600` gives up if the server goes quiet for 10 minutes.
CLIENT_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=600)


def parse_scheduled_release_date(value: str) -> datetime:
    """
    Parse an ISO 8601 release date into an aware `datetime`.
    """
    try:
        # Upper-cased to match the task schema's RFC 3339 check, which accepts a
        # lowercase `t` separator and `z` offset that `fromisoformat` would reject.
        parsed = datetime.fromisoformat(value.upper())
    except (AttributeError, TypeError, ValueError):
        raise VivoUpdateException(
            "Could not read {!r} as a scheduled release date. It has to be an ISO 8601 datetime with a UTC offset, for example '2026-10-01T09:00:00Z'.".format(
                value
            )
        ) from None

    if parsed.tzinfo is None:
        raise VivoUpdateException(
            "The scheduled release date {!r} has no UTC offset, so the time it means depends on "
            "where it is read. Give one, for example '2026-10-01T09:00:00Z'.".format(value)
        )

    return parsed


def latest_schedulable_release_date(now: datetime) -> datetime:
    """
    The latest release date vivo will accept, relative to `now`.
    """
    return (now + timedelta(days=MAX_SCHEDULE_DAYS_AHEAD)).replace(hour=23, minute=59, second=0, microsecond=0)


def _as_online_time(when: datetime) -> int:
    """`onlineTime` is a millisecond epoch."""
    return int(when.timestamp() * 1000)


# Interface method names.
METHOD_UPLOAD_APK = "app.upload.apk"
METHOD_UPDATE_BASIC_INFO = "app.update.basic.info"
METHOD_UPDATE_SUBMIT = "app.update.submit"
METHOD_APP_DETAIL = "app.detail"


def check_can_publish(
    package_name: str,
    apks: List[Tuple[Any, Dict[str, Any]]],
    rollout_rate: Optional[int],
    submit: bool = False,
    scheduled_release_date: Optional[datetime] = None,
) -> None:
    """
    Refuse the requests the vivo publishing API cannot express: a staged rollout
    (`app.update.submit` publishes to every user at once), more than one APK (a vivo app
    version holds a single APK), and a schedule vivo cannot apply.

    These are local checks and run ahead of the `dry_run` bail-out, so a task that can
    never be committed also fails on a dry run.
    """
    if rollout_rate is not None:
        raise VivoUpdateException(
            "The vivo app store has no staged rollout: `{}` publishes to all users at once. A rollout of "
            "{}% was requested for {}, which vivo cannot honour, so nothing was uploaded. Remove the "
            "rollout percentage to publish a full release.".format(METHOD_UPDATE_SUBMIT, rollout_rate, package_name)
        )

    if len(apks) != 1:
        raise VivoUpdateException(
            "The vivo app store holds a single APK per app version, but {} were given for {}: [{}]. Publishing "
            "one of a multi-architecture set would ship that architecture to every user, so nothing was "
            "uploaded.".format(len(apks), package_name, ", ".join(fd.name for fd, _ in apks))
        )

    if scheduled_release_date is None:
        return

    if not submit:
        raise VivoUpdateException(
            "A scheduled release date ({}) was given for {} without `submit`. vivo only applies the schedule "
            "when the release is submitted with `{}`, so the date would be dropped and the APK left "
            "unsubmitted. Set `submit` to schedule it.".format(scheduled_release_date.isoformat(), package_name, METHOD_UPDATE_SUBMIT)
        )

    now = datetime.now(timezone.utc)
    if scheduled_release_date <= now:
        raise VivoUpdateException(
            "The scheduled release date {} for {} has already passed (it is now {}). vivo cannot publish at a "
            "time that has gone, and submitting anyway would publish immediately, so nothing was "
            "uploaded.".format(scheduled_release_date.isoformat(), package_name, now.isoformat(timespec="seconds"))
        )

    latest = latest_schedulable_release_date(now)
    if scheduled_release_date > latest:
        raise VivoUpdateException(
            "The scheduled release date {} for {} is further ahead than vivo accepts. The latest the Developers "
            "console will schedule is {}, {} days out, so nothing was uploaded.".format(
                scheduled_release_date.isoformat(), package_name, latest.isoformat(timespec="minutes"), MAX_SCHEDULE_DAYS_AHEAD
            )
        )


class VivoAppStore:
    """
    High level wrapper to make actions on application on the vivo app store
    """

    def __init__(self, access_key: str, access_secret: str, dry_run: bool = False, basic_info_fallback: Optional[Dict[str, Any]] = None):
        self.api = VivoAppStoreApi(access_key, access_secret)
        self._dry_run = dry_run
        # Values for the mandatory `app.update.basic.info` fields, used only where
        # `app.detail` reports nothing. See `AppContentInfo`.
        self._basic_info_fallback = basic_info_fallback

    async def __aenter__(self) -> "VivoAppStore":
        await self.api.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.api.__aexit__(*args)

    async def upload_apks(self, package_name, apks, rollout_rate, submit=False, scheduled_release_date=None):
        """
        Upload the given APK for `package_name`, bind it to the app, and submit it for
        release when `submit` is set. vivo keys every interface on the package name, so
        there is no app id to resolve first.

        The bind is its own call: `app.update.submit` carries no APK reference, so
        `app.update.basic.info` is what attaches the upload. It runs even when `submit`
        is False, leaving a staged release a human can finish in the console.

        `scheduled_release_date` is an aware `datetime` to publish at; vivo only applies
        it on the submit call, so it requires `submit`.

        Exactly one APK is accepted and `rollout_rate` must be None; see
        `check_can_publish`.
        """
        check_can_publish(package_name, apks, rollout_rate, submit=submit, scheduled_release_date=scheduled_release_date)

        if self._dry_run:
            logger.warning("No APKs were uploaded since `dry_run` was `True`")
            return

        fd, metadata = apks[0]
        file_name = build_apk_file_name(metadata)

        # Resolved before the upload: the bind needs fields the upload cannot supply, so
        # a gap costs one round trip rather than a wasted multi-hundred-megabyte upload.
        app_detail = await self.api.get_app_detail(package_name)
        content_info = AppContentInfo(app_detail, fallback=self._basic_info_fallback)

        logger.info("Uploading %s...", file_name)
        upload = await self.api.upload_apk(package_name, fd.name, file_name)
        serial_number = upload["serialNumber"]
        logger.info(
            "Uploaded %s as serial number %s (versionCode %s, versionName %s)",
            file_name,
            serial_number,
            upload.get("versionCode"),
            upload.get("versionName"),
        )

        await self.api.update_basic_info(package_name, serial_number, content_info)
        logger.info("Bound serial number %s to %s", serial_number, package_name)

        if not submit:
            logger.warning("The APK was uploaded and bound to the app but NOT submitted for release. Set `submit` to release it.")
            return

        if scheduled_release_date is None:
            logger.info("Submitting %s for verification and immediate publication to all users...", package_name)
            await self.api.update_submit(package_name, ONLINE_TYPE_PUBLISH_NOW)
        else:
            now = datetime.now(timezone.utc)
            if scheduled_release_date <= now:
                raise VivoUpdateException(
                    "The scheduled release date {} for {} passed while the APK was uploading (it is now {}). Submitting now "
                    "would publish immediately, so the APK was left uploaded and bound but NOT submitted. Re-run with a later "
                    "date, or submit it in the vivo Developers console.".format(
                        scheduled_release_date.isoformat(), package_name, now.isoformat(timespec="seconds")
                    )
                )

            logger.info("Submitting %s for verification and publication at %s...", package_name, scheduled_release_date.isoformat())
            await self.api.update_submit(package_name, ONLINE_TYPE_SCHEDULED, online_time=_as_online_time(scheduled_release_date))

        logger.info("Submitted %s for verification and publication", package_name)


class VivoAppStoreApi:
    """
    A low level wrapper around the vivo publishing API. You should probably use the `VivoAppStore` wrapper around this instead
    """

    def __init__(self, access_key: str, access_secret: str):
        self._access_key = access_key
        self._access_secret = access_secret
        self._client = aiohttp.ClientSession(timeout=CLIENT_TIMEOUT)

    async def __aenter__(self) -> "VivoAppStoreApi":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.close()

    def _default_headers(self) -> Dict[str, str]:
        """
        Returns headers necessary for every request. The credentials travel in the
        request body as the `access_key` and `sign` parameters, not in a header.
        """
        return {"User-Agent": "mozapkpublisher"}

    def _signed_params(self, method_name: str, biz_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return build_signed_params(method_name, self._access_key, self._access_secret, biz_params)

    async def _post(self, method_name: str, data: Any) -> Any:
        # Every interface posts to the same route, so `method` is what identifies the
        # call. The signed parameters are not logged: they carry the access key and the
        # signature derived from the access secret.
        url = urljoin(BASE_URL, ROUTER_ROUTE)
        logger.info("POST %s (method=%s)", url, method_name)

        return await request(
            self._client,
            "POST",
            ROUTER_ROUTE,
            base_url=BASE_URL,
            headers=self._default_headers(),
            raise_for_status=raise_for_status_with_message,
            raise_for_ret_code=raise_for_response_code,
            data=data,
        )

    async def upload_apk(self, package_name: str, file_path: str, name: str) -> Dict[str, Any]:
        """
        Upload an APK for the given package and return the response's `data` object,
        which carries the `serialNumber` identifying the uploaded binary.

        `fileMd5` is mandatory and the store compares it against what it receives,
        rejecting a mismatch with subCode A0114.

        method: app.upload.apk
        """
        file_md5 = file_md5sum(file_path)
        params = self._signed_params(METHOD_UPLOAD_APK, {"packageName": package_name, "fileMd5": file_md5})

        form = aiohttp.FormData()
        with open(file_path, "rb") as file:
            # Every signed parameter rides as its own multipart field alongside the
            # binary. A parameter must never be sent in both the body and the query
            # string: a duplicate breaks signature validation.
            for key, value in params.items():
                form.add_field(key, str(value))
            form.add_field("file", file, filename=name)
            body = await self._post(METHOD_UPLOAD_APK, form)

        data = response_data(body) or {}
        if not data.get("serialNumber"):
            raise VivoUploadException("The upload result didn't contain a serial number: {}".format(body))

        # vivo echoes back the MD5 it computed over what it received.
        returned_md5 = data.get("fileMd5")
        if returned_md5 and returned_md5 != file_md5:
            raise VivoUploadException("The upload result gave a file MD5 different than what was uploaded. Got {}, expected {}".format(returned_md5, file_md5))

        return data

    async def update_basic_info(self, package_name: str, apk_serial_number: str, content_info: AppContentInfo) -> Dict[str, Any]:
        """
        Bind an uploaded APK to the app by its `serialNumber`.

        `content_info` is an `AppContentInfo` built from `get_app_detail`; this interface
        replaces the whole basic-info record rather than patching one field, so the app's
        current mandatory values are re-sent alongside the new serial. See
        `AppContentInfo.as_basic_info_payload`.

        method: app.update.basic.info
        """
        payload = content_info.as_basic_info_payload(package_name, apk_serial_number)

        return await self._post(METHOD_UPDATE_BASIC_INFO, self._signed_params(METHOD_UPDATE_BASIC_INFO, payload))

    async def update_submit(
        self,
        package_name: str,
        online_type: int = ONLINE_TYPE_PUBLISH_NOW,
        online_time: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit the app for verification and publication. `online_type` is
        ONLINE_TYPE_PUBLISH_NOW to publish as soon as it passes review, or
        ONLINE_TYPE_SCHEDULED to publish at `online_time` (a millisecond timestamp).

        Note this carries no reference to an APK: it submits whatever binary is
        currently bound to the app, so `update_basic_info` has to have run first.

        method: app.update.submit
        """
        if online_type == ONLINE_TYPE_SCHEDULED and online_time is None:
            raise VivoUpdateException("A scheduled publication requires `online_time`, which vivo cannot infer.")

        return await self._post(
            METHOD_UPDATE_SUBMIT,
            self._signed_params(
                METHOD_UPDATE_SUBMIT,
                {"packageName": package_name, "onlineType": online_type, "onlineTime": online_time, "remark": remark},
            ),
        )

    async def get_app_detail(self, package_name: str) -> Dict[str, Any]:
        """
        Get the details of the app with the given package name, including its current
        `status` and the `versionCode`/`apkMd5` of the binary it currently holds.

        method: app.detail
        """
        body = await self._post(METHOD_APP_DETAIL, self._signed_params(METHOD_APP_DETAIL, {"packageName": package_name}))

        return response_data(body) or {}
