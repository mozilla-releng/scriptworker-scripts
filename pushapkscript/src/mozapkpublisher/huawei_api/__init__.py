from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from .content_info import AppContentInfo
from .utils import raise_for_status_with_message, raise_for_ret_code
from .result_codes import (
    PACKAGE_COMPILING,
    PACKAGE_PROCESSING_MESSAGES,
    PERMANENT_SUBMIT_SUB_CODES,
    SUBMIT_QUERY_FAILED,
)
from .error import HuaweiUploadException, HuaweiUpdateException
from mozapkpublisher.common.store_api import build_apk_file_name, request
from mozapkpublisher.common.utils import file_sha256sum
from .auth import create_jwt

import aiohttp
import asyncio
import logging
import os.path
import time

BASE_URL = "https://connect-api.cloud.huawei.com/"
logger = logging.getLogger(__name__)

# `releaseType` values accepted by the AppGallery publishing API. There is no value 2:
# a phased release is 3, and it only works for an app that already has a released version.
# https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-0000001158245061
RELEASE_TYPE_FULL_ROLLOUT = 1
RELEASE_TYPE_PHASED_ROLLOUT = 3

# AppGallery requires both a start and an end time for a phased release and cannot infer
# either, so the length of the window is a policy decision made here.
PHASED_ROLLOUT_WINDOW = timedelta(days=7)

# Format of `phasedReleaseStartTime`/`phasedReleaseEndTime`, documented as
# `yyyy-MM-ddTHH:mm:ssZZ` with the example 2015-01-01T01:01:01+0800. The offset carries no
# colon, which is why this is spelled out rather than using `datetime.isoformat()` -- that
# emits +00:00.
PHASED_ROLLOUT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# AppGallery parses uploaded packages asynchronously and rejects `app-submit` until that
# finishes, so the submission is retried rather than sent once.
#
# The delay cannot go below two minutes: consecutive `app-submit` calls made less than
# that apart are rejected outright, so a shorter retry would fail on the interval rather
# than on the package. Huawei's own message on 204144727 asks for a retry 3 to 5 minutes
# later, which the 10 minute budget covers.
# https://developer.huawei.com/consumer/en/doc/AppGallery-connect-Guides/agcapi-pub-releasenotes-0000001111685226
SUBMIT_MINIMUM_RETRY_DELAY = 120
SUBMIT_RETRY_DELAY = 120
SUBMIT_RETRY_TIMEOUT = 600


def _is_package_still_processing(ret):
    """
    Whether `app-submit` failed only because AppGallery hasn't finished parsing the
    package that was just uploaded, and is therefore worth retrying.

    Decided by result code wherever a code is decisive, and only by message where none
    is. PACKAGE_COMPILING has a single meaning, so it decides alone. SUBMIT_QUERY_FAILED
    is returned both for permanent failures and for a package still being parsed, so a
    documented sub-code in the message vetoes a retry, and failing that the narrow set of
    observed "still parsing" phrases allows one. Anything unrecognised is treated as
    permanent, so a new failure mode surfaces immediately instead of stalling for the
    whole timeout. See `result_codes` for the provenance of each value.
    """
    code = ret.get("code")
    if code == PACKAGE_COMPILING:
        return True
    if code != SUBMIT_QUERY_FAILED:
        return False

    message = ret.get("msg") or ""
    if any(sub_code in message for sub_code in PERMANENT_SUBMIT_SUB_CODES):
        return False

    return any(fragment in message.lower() for fragment in PACKAGE_PROCESSING_MESSAGES)


def build_phased_release(rollout_rate, start_time=None):
    """
    Build the `app-submit` request body for a phased release. All four fields are
    mandatory whenever `releaseType` is RELEASE_TYPE_PHASED_ROLLOUT, and
    `phasedReleasePercent` is a string with two decimals and no percent sign.

    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-0000001158245061
    """
    if not 0 < rollout_rate <= 100:
        raise HuaweiUpdateException(
            "Rollout percentage must be in (0, 100]. Value given: {}".format(rollout_rate)
        )

    start_time = start_time or datetime.now(timezone.utc)
    percent = "{:.2f}".format(rollout_rate)
    return {
        "phasedReleaseStartTime": start_time.strftime(PHASED_ROLLOUT_TIME_FORMAT),
        "phasedReleaseEndTime": (start_time + PHASED_ROLLOUT_WINDOW).strftime(PHASED_ROLLOUT_TIME_FORMAT),
        "phasedReleasePercent": percent,
        "phasedReleaseDescription": "Phased rollout to {}% of users".format(percent),
    }


class HuaweiAppGallery:
    """
    High level wrapper to make actions on application on the huawei app gallery
    """

    def __init__(self, credentials: Dict[str, str], dry_run: bool = False):
        self.api = HuaweiAppGalleryApi(credentials)
        self._dry_run = dry_run

    async def __aenter__(self) -> "HuaweiAppGallery":
        await self.api.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.api.__aexit__(*args)

    async def upload_apks(self, package_name, apks, rollout_rate, submit=False):
        """
        Upload the APKs passed as arguments. The app to be updated will be inferred from
        the package name.

        If `rollout_rate` is not None, the submission is a phased release
        (`releaseType=3`) targeting that percentage of users over
        `PHASED_ROLLOUT_WINDOW`. AppGallery only accepts a phased release for an app
        that already has a released version, so the very first submission for a
        package has to be a full rollout.
        """
        if self._dry_run:
            logger.warning('No APKs were uploaded since `dry_run` was `True`')
            return

        app_id = await self.infer_app_id_from_package_name(package_name)
        logger.info('Resolved app ID %s for package %s', app_id, package_name)

        files = []
        for apk in apks:
            fd, metadata = apk

            file_name = build_apk_file_name(metadata)
            logger.info('Uploading %s...', file_name)
            file_dest_url = await self.upload_file(app_id, fd.name, file_name)
            files.append({"fileName": file_name, "fileDestUrl": file_dest_url})
            logger.info('Uploaded %s', file_name)

        await self.api.update_app_file_info(app_id, files)
        logger.info('Bound %s binaries to app %s: %s', len(files), app_id, ", ".join(f["fileName"] for f in files))

        if not submit:
            logger.warning(
                'Binaries were uploaded but NOT submitted for release. Pass `--submit` to release them.'
            )
            return

        if rollout_rate is None:
            logger.info('Submitting app %s for a FULL release to all users...', app_id)
            await self.submit_app(app_id, RELEASE_TYPE_FULL_ROLLOUT)
            logger.info('Submitted app %s for full release', app_id)
        else:
            logger.info(
                'Submitting app %s for a PHASED release to %s%% of users over %s days...',
                app_id, rollout_rate, PHASED_ROLLOUT_WINDOW.days,
            )
            await self.submit_app(
                app_id, RELEASE_TYPE_PHASED_ROLLOUT, build_phased_release(rollout_rate)
            )
            logger.info('Submitted app %s for a phased release to %s%% of users', app_id, rollout_rate)

    async def submit_app(self, app_id, release_type, phased_release=None):
        """
        Submit the app for release once AppGallery has finished parsing the binary that
        was just bound to it.

        Packages are parsed asynchronously and `app-submit` fails while that is in
        flight, so the first attempt goes out immediately -- a small package is often
        ready straight away -- and is then retried every `SUBMIT_RETRY_DELAY` seconds
        until `SUBMIT_RETRY_TIMEOUT`. Any other failure is raised on the first attempt.

        https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-0000001158245061
        """
        deadline = time.monotonic() + SUBMIT_RETRY_TIMEOUT

        while True:
            body = await self.api.submit_app(
                app_id, release_type=release_type, phased_release=phased_release, check_ret=False
            )
            ret = body.get("ret") or {}

            if not _is_package_still_processing(ret):
                raise_for_ret_code(body)
                return body

            if time.monotonic() >= deadline:
                raise HuaweiUpdateException(
                    "AppGallery was still processing the uploaded package {} seconds after it was bound to the "
                    "release, so it could not be submitted: ret.code={}: {}. The binary is uploaded, so the "
                    "release can still be submitted from the AppGallery Connect console.".format(
                        SUBMIT_RETRY_TIMEOUT, ret.get("code"), ret.get("msg")
                    )
                )

            logger.info(
                "AppGallery is still processing the package (%s). Retrying the submission in %s seconds.",
                ret.get("msg"),
                SUBMIT_RETRY_DELAY,
            )
            await asyncio.sleep(SUBMIT_RETRY_DELAY)

    async def upload_file(self, app_id, file, name):
        """
        Uploads a file to the huawei app gallery and returns its file destination URL.

        That URL is the storage reference the upload step returns for the uploaded
        binary. It is passed to `update_app_file_info` to bind the binary to the app
        release.

        The upload response misspells the key as `fileDestUlr`, while the
        `app-file-info` request that consumes it spells it `fileDestUrl`. Both
        spellings are accepted here so the client keeps working if Huawei ever fixes
        the typo.

        The file's SHA-256 is sent to `get_upload_url` so the AppGallery store
        verifies the integrity of the uploaded package against it.
        """
        sha256 = file_sha256sum(file)
        upload_info = await self.api.get_upload_url(app_id, suffix=os.path.splitext(name)[1].lstrip(".") or "apk", sha256=sha256)
        file_upload = await self.api.upload_file(upload_info["uploadUrl"], upload_info["authCode"], file, name)

        file_dest_url = file_upload.get("fileDestUlr") or file_upload.get("fileDestUrl")
        if not file_dest_url:
            raise HuaweiUploadException(
                "The upload result didn't contain a file destination URL: {}".format(file_upload)
            )
        return file_dest_url

    async def infer_app_id_from_package_name(self, package_name):
        """
        Returns the app ID related to the package name provided.

        `appid-list` already filters on `packageName` server-side. Its entries are
        `{"key": <app name>, "value": <app id>}` pairs and carry no package name of
        their own, so there is nothing left to match on here.
        """
        result = await self.api.app_id_list(package_name=package_name)
        apps = result.get("appids") or []
        app_ids = [app["value"] for app in apps]

        if len(app_ids) > 1:
            raise HuaweiUpdateException(
                f"Found multiple app IDs for the package name {package_name}: {app_ids}. "
                "Refusing to guess which one to publish to."
            )
        if not app_ids:
            raise HuaweiUpdateException(
                f"Couldn't find an app ID for the following package name {package_name}."
            )

        return app_ids[0]


class HuaweiAppGalleryApi:
    """
    A low level wrapper around the huawei app gallery API. You should probably use the `HuaweiAppGallery` wrapper around this instead
    """

    def __init__(self, credentials: Dict[str, str]):
        self._credentials = credentials
        self._client = aiohttp.ClientSession()

    async def __aenter__(self) -> "HuaweiAppGalleryApi":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.close()

    def _default_headers(self) -> Dict[str, str]:
        """
        Returns headers necessary for every authenticated request. In Service Account
        mode the bearer token is a freshly self-signed JWT (the JWT *is* the access
        token), so there is no separate `client_id` header.
        https://developer.huawei.com/consumer/en/doc/appgallery-connect-guides/agc-remoteconfig-getapicredentials-0000002539183415
        """
        token = create_jwt(
            self._credentials["key_id"],
            self._credentials["sub_account"],
            self._credentials["private_key"],
        )
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": "mozapkpublisher",
        }

    async def _request(
        self,
        method: str,
        route: str,
        *,
        base_url: str = BASE_URL,
        check_ret: bool = True,
        **kwargs: Any,
    ) -> Any:
        return await request(
            self._client,
            method,
            route,
            base_url=base_url,
            headers=self._default_headers(),
            raise_for_status=raise_for_status_with_message,
            raise_for_ret_code=raise_for_ret_code if check_ret else None,
            **kwargs,
        )

    async def get_upload_url(self, app_id: str, suffix: str = "apk", release_type: int = RELEASE_TYPE_FULL_ROLLOUT, sha256: str = None) -> Dict[str, Any]:
        """
        Get an upload URL for a binary. When `sha256` (the hex digest of the file) is
        provided, the store verifies the integrity of the uploaded package against it.

        `/api/publish/v2/upload-url` is undocumented: the reference page below describes
        `/api/publish/v2/upload-url/for-obs`, which is a separate endpoint rather than a
        rename. `for-obs` rejects this parameter set with "Parameter is [fileName].
        Parameter is required.", and its docs additionally make `chineseMainlandFlag`
        mandatory for developers registered outside the Chinese mainland.

        We call the undocumented route because it is the one that accepts these
        parameters, confirmed against the production API. Being undocumented, it may be
        withdrawn without notice; `for-obs` is then the migration target, and moving to it
        means supplying those two extra parameters rather than only changing the path.

        https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-upload-url-new-0000001111685200
        """
        params = {"appId": app_id, "suffix": suffix, "releaseType": release_type}
        if sha256 is not None:
            params["sha256"] = sha256
        return await self._request("GET", "/api/publish/v2/upload-url", params=params)

    async def upload_file(self, upload_url: str, auth_code: str, file_path: str, name: str) -> Dict[str, Any]:
        """
        Upload a file using a previously obtained upload URL + auth code.

        https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-upload-file-new-0000001111845090
        """
        original_file_size = os.path.getsize(file_path)

        form = aiohttp.FormData()
        with open(file_path, "rb") as file:
            form.add_field("authCode", auth_code)
            form.add_field("fileCount", "1")
            form.add_field("file", file, filename=name)

            # The upload URL is one-off and absolute (returned by get_upload_url); urljoin
            # leaves it untouched. The upload response has no `ret` envelope, so no in-band check.
            body = await request(
                self._client,
                "POST",
                upload_url,
                base_url=BASE_URL,
                headers=self._default_headers(),
                raise_for_status=raise_for_status_with_message,
                data=form,
            )

        result_list = body.get("result", {}).get("UploadFileRsp", {}).get("fileInfoList", [])
        if not result_list:
            raise HuaweiUploadException(
                "The upload result didn't contain a fileInfoList entry: {}".format(body)
            )
        result = result_list[0]

        # Huawei doesn't return a checksum for the uploaded binary, so the best we
        # can do is validate that the reported size matches what we sent.
        if int(result.get("size", 0)) != original_file_size:
            raise HuaweiUploadException(
                "The upload result gave a file size different than what was uploaded. Got {}, expected {}".format(
                    result.get("size"), original_file_size
                )
            )

        return result

    async def update_app_file_info(self, app_id: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Update the file info bound to an app release.

        https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-file-info-0000001111685202
        """
        payload = AppContentInfo({"appId": app_id}).as_file_info_payload(files)
        return await self._request(
            "PUT",
            "/api/publish/v2/app-file-info",
            params={"appId": app_id},
            json=payload,
        )

    async def submit_app(
        self,
        app_id: str,
        release_type: int = RELEASE_TYPE_FULL_ROLLOUT,
        phased_release: Optional[Dict[str, str]] = None,
        check_ret: bool = True,
    ) -> Dict[str, Any]:
        """
        Submit the application for release. `release_type` is RELEASE_TYPE_FULL_ROLLOUT (1) for a
        full release and RELEASE_TYPE_PHASED_ROLLOUT (3) for a phased release.

        A full release takes no request body. A phased release requires `phased_release`,
        the body built by `build_phased_release`.

        Pass `check_ret=False` to get the raw body back instead of raising on a non-zero
        `ret.code`, so the caller can tell a retryable failure from a terminal one.

        https://developer.huawei.com/consumer/en/doc/appgallery-connect-references/agcapi-app-submit-0000001158245061
        """
        kwargs = {}
        if phased_release is not None:
            kwargs["json"] = phased_release

        return await self._request(
            "POST",
            "/api/publish/v2/app-submit",
            params={"appId": app_id, "releaseType": release_type},
            check_ret=check_ret,
            **kwargs,
        )

    async def get_app_info(self, app_id: str) -> AppContentInfo:
        """
        Get the app info for the given app ID.

        https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-info-query-0000001158365045
        """
        result = await self._request(
            "GET", "/api/publish/v2/app-info", params={"appId": app_id}
        )

        return AppContentInfo(result.get("appInfo", {}))

    async def app_id_list(self, package_name: str) -> Dict[str, Any]:
        """
        Return the appId list for a given package name.

        https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-appid-list-0000001111845086
        """
        return await self._request(
            "GET",
            "/api/publish/v2/appid-list",
            params={"packageName": package_name},
        )
