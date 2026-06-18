from typing import Dict, Any, List
from .content_info import AppContentInfo
from .utils import raise_for_status_with_message, raise_for_ret_code
from .error import HuaweiUploadException, HuaweiUpdateException
from mozapkpublisher.common.store_api import build_apk_file_name, request
from mozapkpublisher.common.utils import file_sha256sum
from .auth import create_jwt

import aiohttp
import logging
import os.path

BASE_URL = "https://connect-api.cloud.huawei.com/"
logger = logging.getLogger(__name__)

# `releaseType` values accepted by the AppGallery publishing API.
RELEASE_TYPE_FULL_ROLLOUT = 1
RELEASE_TYPE_PHASED_ROLLOUT = 2


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

        If `rollout_rate` is not None, the submission uses `releaseType=2` (phased
        release). Setting the target rollout percentage is not handled here; that's
        managed in the AppGallery Connect console (or via a follow-up phased-release
        endpoint that is not yet wired up).
        """
        if self._dry_run:
            logger.warning('No APKs were uploaded since `dry_run` was `True`')
            return

        app_id = await self.infer_app_id_from_package_name(package_name)

        files = []
        for apk in apks:
            fd, metadata = apk

            file_name = build_apk_file_name(metadata)
            file_dest_url = await self.upload_file(app_id, fd.name, file_name)
            files.append({"fileName": file_name, "fileDestUrl": file_dest_url})

        await self.api.update_app_file_info(app_id, files)

        if submit:
            release_type = RELEASE_TYPE_PHASED_ROLLOUT if rollout_rate is not None else RELEASE_TYPE_FULL_ROLLOUT
            await self.api.submit_app(app_id, release_type=release_type)

    async def upload_file(self, app_id, file, name):
        """
        Uploads a file to the huawei app gallery and returns its `fileDestUrl`.

        `fileDestUrl` is the storage reference the upload step returns for the
        uploaded binary. It is passed to `update_app_file_info` to bind the binary
        to the app release.

        The file's SHA-256 is sent to `get_upload_url` so the AppGallery store
        verifies the integrity of the uploaded package against it.
        """
        sha256 = file_sha256sum(file)
        upload_info = await self.api.get_upload_url(app_id, suffix=os.path.splitext(name)[1].lstrip(".") or "apk", sha256=sha256)
        file_upload = await self.api.upload_file(upload_info["uploadUrl"], upload_info["authCode"], file, name)
        return file_upload["fileDestUrl"]

    async def infer_app_id_from_package_name(self, package_name):
        """
        Returns the app ID related to the package name provided.
        """
        result = await self.api.app_id_list(package_name=package_name)
        apps = result.get("appids", []) or []
        matches = [app["value"] for app in apps if app.get("package") == package_name]

        if len(matches) > 1:
            raise HuaweiUpdateException(
                f"Found multiple app IDs for the package name {package_name}: {matches}. "
                "Refusing to guess which one to publish to."
            )
        if matches:
            return matches[0]

        raise HuaweiUpdateException(
            f"Couldn't find an app ID for the following package name {package_name}."
        )


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

    async def submit_app(self, app_id: str, release_type: int = RELEASE_TYPE_FULL_ROLLOUT) -> Dict[str, Any]:
        """
        Submit the application for release. `release_type` is RELEASE_TYPE_FULL_ROLLOUT (1) for a
        full release and RELEASE_TYPE_PHASED_ROLLOUT (2) for a phased release.

        https://developer.huawei.com/consumer/en/doc/appgallery-connect-references/agcapi-app-submit-0000001158245061
        """
        return await self._request(
            "POST",
            "/api/publish/v2/app-submit",
            params={"appId": app_id, "releaseType": release_type},
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
