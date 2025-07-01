from typing import Dict, Any, List
from .content_info import AppContentInfo
from .utils import raise_for_status_with_message
from .error import SgsUploadException, SgsContentInfoException, SgsUpdateException
from urllib.parse import urljoin

import aiohttp
import logging
import os.path

BASE_DEVAPI_URL = "https://devapi.samsungapps.com/"
BASE_SELLER_URL = "https://seller.samsungapps.com/"
logger = logging.getLogger(__name__)


class SamsungGalaxyStore:
    """
    High level wrapper to make actions on application on the samsung galaxy store
    """

    def __init__(self, service_account_id: str, access_token: str, dry_run: bool = False):
        self.api = SamsungGalaxyApi(service_account_id, access_token)
        self._dry_run = dry_run

    async def __aenter__(self) -> "SamsungGalaxyStore":
        await self.api.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.api.__aexit__(*args)

    async def upload_apks(self, package_name, apks, rollout_rate, submit=False):
        """
        Upload the APKs passed as arguments. The app to be updated will be infered from the package name.
        If the rollout_rate is not None, all new apks will be added to a staged rollout with that rate.

        Notes: The app needs to be in the `FOR_SALE` status and needs to not be in the middle of an update.
        """
        if self._dry_run:
            logger.warning('No APKs were uploaded since `dry_run` was `True`')
            return

        content_id = await self.infer_content_id_from_package_name(package_name)
        content_info = await self.api.get_content_info(content_id)

        if len(content_info) != 1 or content_info[0].status != "FOR_SALE":
            raise SgsUpdateException(
                f"The app with the content ID {content_id} is currently being updated. You'll have to cancel it manually before proceeding"
            )

        current_info = content_info[0]

        # Because infer_content_id_from_package_name relies on a binary with the package name existing, we know that binary_list here is not empty
        last_binary = max((binary for binary in current_info.binary_list), key=lambda binary: int(binary["binarySeq"]))
        last_binary_id = int(last_binary["binarySeq"])

        for apk in apks:
            fd, metadata = apk

            file_name = "{}-{}-{}.apk".format(metadata["package_name"], metadata["architecture"], metadata["version_name"])
            file_key = await self.upload_file(fd.name, file_name)
            new_binary = {
                "fileName": os.path.basename(fd.name),
                "versionCode": metadata["version_code"],
                "binarySeq": last_binary_id + 1,
                "packageName": metadata["package_name"],
                "apiminSdkVersion": metadata["api_level"],
                "apimaxSdkversion": None,
                "iapSdk": last_binary["iapSdk"],
                "gms": last_binary["gms"],
                "filekey": file_key,
            }

            current_info.add_binary(new_binary)
            last_binary_id += 1

        await self.api.update_content_info(current_info)

        if rollout_rate is not None:
            # Grab the actual content as samsung requires us to
            try:
                new_content_info = next(ci for ci in await self.api.get_content_info(content_id) if ci.status == "UPDATING")
            except StopIteration:
                raise SgsUpdateException(
                    "The API didn't return a content info with the UPDATING status. Unable to create a rollout"
                )

            new_binaries = [
                binary["binarySeq"]
                for binary in new_content_info.binary_list
                if binary["versionCode"] in (apk["version_code"] for (_, apk) in apks)
            ]
            for new_bin in new_binaries:
                await self.api.add_binary_to_staged_rollout(content_id, new_bin)

            await self.api.enable_staged_rollout(content_id, rollout_rate)

        if submit:
            await self.api.submit_app(content_id)

    async def upload_file(self, file, name):
        """
        Uploads a file to the samsung galaxy store and returns its file key
        """
        session_id = (await self.api.create_upload_session_id())["sessionId"]
        file_upload = await self.api.upload_file(session_id, file, name)
        return file_upload["fileKey"]

    async def infer_content_id_from_package_name(self, package_name):
        """
        Returns the content ID related to the package name provided. This is possible
        because samsung doesn't allow reusing package names between different applications.
        """
        apps = await self.api.app_list()
        for app in apps:
            content_info = await self.api.get_content_info(app["contentId"])

            binaries = content_info[0].binary_list
            for binary in binaries:
                if binary["packageName"] == package_name:
                    return app["contentId"]

        raise SgsUpdateException(
            f"Couldn't find a content ID for the following package name {package_name}."
        )


class SamsungGalaxyApi:
    """
    A low level wrapper around the samsung galaxy API. You should probably use the `SamsungGalaxyStore` wrapper around this instead
    """

    def __init__(self, service_account_id: str, access_token: str):
        self._service_account_id = service_account_id
        self._access_token = access_token
        self._client = aiohttp.ClientSession()

    async def __aenter__(self) -> "SamsungGalaxyApi":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.close()

    def _default_headers(self) -> Dict[str, str]:
        """
        Returns headers necessary for every authenticated request, according to
        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/use-the-access-token.html#Authorization-header-parameters
        """
        return {
            "Authorization": f"Bearer {self._access_token}",
            "service-account-id": self._service_account_id,
            "User-Agent": "mozapkpublisher",
        }

    async def _request(
        self,
        method: str,
        route: str,
        *,
        base_url: str = BASE_DEVAPI_URL,
        **kwargs: Any,
    ) -> Any:
        headers = self._default_headers()
        url = urljoin(base_url, route)

        response = await self._client.request(method, url, headers=headers, **kwargs)

        await raise_for_status_with_message(response)

        body = await response.json()
        return body

    async def check_access_token(self) -> Dict[str, Any]:
        """
        Validate an access token

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/use-the-access-token.html#Validate-an-access-token
        """
        return await self._request("GET", "/auth/checkAccessToken")

    async def revoke_access_token(self) -> Dict[str, Any]:
        """
        Revoke the current access token

        Note: this will leave the current `SamsungGalaxyApi` unable to make any further authenticated calls as it revokes the token in use

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/use-the-access-token.html#Revoke-an-access-token
        """
        return await self._request("DELETE", "/auth/revokeAccessToken")

    async def create_upload_session_id(self) -> Dict[str, Any]:
        """
        Create a session ID required to upload a file.
        The session ID is valid 24h

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/create-session-id.html
        """
        return await self._request("POST", "/seller/createUploadSessionId")

    async def upload_file(
        self, session_id: str, file_path: str, name: str
    ) -> Dict[str, Any]:
        """
        Upload  a file required for app submission or for updating one
        The required `session_id` can be gotten through `create_upload_session_id`.

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/file-upload.html
        """
        original_file_size = os.path.getsize(file_path)

        form = aiohttp.FormData()
        with open(file_path, "rb") as file:
            form.add_field("file", file, filename=name)
            form.add_field("sessionId", session_id)

            # This API uses a different base URL for some reason
            result = await self._request(
                "POST", "/galaxyapi/fileUpload", base_url=BASE_SELLER_URL, data=form
            )

        # Since they don't respond with a checksum, best we can do is validate that the size matches what we expect
        if int(result["fileSize"]) != original_file_size:
            raise SgsUploadException(
                "The upload result gave a file size different than what was uploaded. Got {}, expected {}".format(
                    int(result["fileSize"]), original_file_size
                )
            )

        return result

    async def get_content_info(self, content_id: str) -> List[AppContentInfo]:
        """
        Get the content info for the given content ID.

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/view-sellers-app-details.html
        """
        result = await self._request(
            "GET", "/seller/contentInfo", params={"contentId": content_id}
        )

        if not result:
            raise SgsContentInfoException(
                "The samsung API an unexpected number of items (got {}, expected >=1) for a given content ID".format(
                    len(result)
                )
            )

        content = result[0]
        if content["contentId"] != content_id:
            raise SgsContentInfoException(
                "The samsung API returned information about another content ID than the one given: {}".format(
                    content["contentId"]
                )
            )

        return [AppContentInfo(content) for content in result]

    async def update_content_info(
        self, new_content_info: AppContentInfo
    ) -> Dict[str, Any]:
        """
        Modify app information. Use `get_content_info`, modify the object and pass it into this function

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/modify-app-data.html
        """
        return await self._request(
            "POST", "/seller/contentUpdate", json=new_content_info.as_new_data()
        )

    async def enable_staged_rollout(self, content_id, rollout_rate):
        """
        Create a staged rollout for the given content id at the given rollout rate. Note that this only works for an application currently getting updated.

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/update-staged-rollout-rate.html
        """
        data = {
            "contentId": content_id,
            "function": "ENABLE_ROLLOUT",
            "appStatus": "REGISTRATION",
            "rolloutRate": rollout_rate,
        }

        return await self._request(
            "PUT", "/seller/v2/content/stagedRolloutRate", json=data
        )

    async def add_binary_to_staged_rollout(self, content_id: str, binary_seq: str):
        """
        Add the given binary to the current staged rollout.

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/update-staged-rollout-binary.html
        """

        data = {
            "contentId": content_id,
            "function": "ADD",
            "binarySeq": binary_seq,
        }

        return await self._request(
            "PUT", "/seller/v2/content/stagedRolloutBinary", json=data
        )

    async def submit_app(self, content_id: str):
        """
        Submit the application update to the samsung galaxy store.

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/submit-app.html
        """
        data = {"contentId": content_id}

        return await self._request("POST", "/seller/contentSubmit", json=data)

    async def app_list(self):
        """
        Return a list of all application the current access token has access to.

        https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/view-sellers-app-list.html
        """
        return await self._request("GET", "/seller/contentList")
