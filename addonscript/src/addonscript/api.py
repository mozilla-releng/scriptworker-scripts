"""API helpers for addonscript."""

import hashlib
import os

from aiohttp.client_exceptions import ClientResponseError

from addonscript.exceptions import AMOConflictError, AuthFailedError, AuthInsufficientPermissionsError, FatalSignatureError, SignatureError
from addonscript.task import get_channel
from addonscript.utils import amo_download, amo_get, amo_post, amo_put, get_api_url

# https://addons-server.readthedocs.io/en/latest/topics/api/addons.html#upload-create
UPLOAD_CREATE = "api/v5/addons/upload/"

# https://addons-server.readthedocs.io/en/latest/topics/api/addons.html#upload-detail
UPLOAD_DETAIL = "api/v5/addons/upload/{uuid}/"

# https://addons-server.readthedocs.io/en/latest/topics/api/addons.html#versions-list
VERSION_LIST = "api/v5/addons/addon/{id}/versions/?filter=all_with_unlisted"

# https://addons-server.readthedocs.io/en/latest/topics/api/addons.html#version-detail
VERSION_DETAIL = "api/v5/addons/addon/{id}/versions/{version}/"

# https://addons-server.readthedocs.io/en/latest/topics/api/addons.html#put-create-or-edit
ADDON_CREATE_OR_EDIT = "api/v5/addons/addon/{id}/"

# https://addons-server.readthedocs.io/en/latest/topics/api/v4_frozen/applications.html
# XXX when we want to support multiple products, we'll need to unhardcode the
#     `firefox` below
ADD_APP_VERSION = "api/v4/applications/firefox/{version}/"


async def add_app_version(context, version):
    """Add a new version to AMO.

    Use the `min_version` here, rather than the string with the buildid etc.

    Raises:
        AuthFailedError: If the automation credentials are misconfigured
        AuthInsufficientPermissionsError: If the automation credentials are missing permissions


    """
    url = get_api_url(context, ADD_APP_VERSION, version=version)

    try:
        result = await amo_put(context, url, data=None)
    except ClientResponseError as exc:
        if exc.status == 401:
            raise AuthFailedError("Addonscript credentials are misconfigured")
        elif exc.status == 403:
            raise AuthInsufficientPermissionsError("Addonscript creds are missing permissions")
        raise exc

    return result


async def check_upload(context, uuid):
    """Check on the status of file upload identified by `uuid`

    Raises:
        SignatureError: If the upload is awaiting processing
        FatalSignatureError: If validation errors occurred
    """
    url = get_api_url(context, UPLOAD_DETAIL, uuid=uuid)
    result = await amo_get(context, url)
    if not result["processed"]:
        # retry
        raise SignatureError("upload not yet processed")
    if not result["valid"]:
        raise FatalSignatureError(f"Automated validation produced errors: {result['validation']}")


async def do_upload(context, locale):
    """Upload the language pack for `locale` to AMO.

    Returns the JSON response from AMO
    """
    locale_info = context.locales[locale]
    url = get_api_url(context, UPLOAD_CREATE)
    with open(locale_info["unsigned"], "rb") as file:
        data = {"channel": get_channel(context.task), "upload": file}
        return await amo_post(context, url, data)


async def do_create_version(context, locale, upload_uuid):
    """Create a new version for the `locale` language pack on AMO.

    Returns the version's identifier

    Raises:
        AMOConflictError: If the version already exists for this addon
    """
    locale_info = context.locales[locale]
    langpack_id = locale_info["id"]
    url = get_api_url(context, ADDON_CREATE_OR_EDIT, id=langpack_id)
    data = {
        "categories": {"firefox": ["general"]},
        "name": {"en-US": locale_info["name"]},
        "summary": {"en-US": locale_info["description"]},
        "version": {
            "license": "MPL-2.0",
            "upload": upload_uuid,
        },
    }
    try:
        result = await amo_put(context, url, json=data)
    except ClientResponseError as exc:
        if exc.status == 409:
            raise AMOConflictError("Addon <{}> already present on AMO with version <{}>".format(langpack_id, locale_info["version"]))
        raise

    return result["version"]


async def get_signed_addon_info(context, locale, version_id):
    """Query AMO to get the location of the signed XPI.

    This function should be called within `scriptworker.utils.retry_async()`.

    Raises:
        SignatureError: If the metadata lacks something or if the server-side Automated validation
        reported something. This is a retryable exception.
        FatalSignatureError: if there is a nonrecoverable error from this submission, e.g. validation errors.
        aiohttp.ClientError: If there is some sort of networking issue.
        asyncio.TimeoutError: If the network request times out.

    Returns the XPI url, size and hash

    """
    # XXX Retry is done at top-level. Avoiding a retry here avoids never-ending retries cascade
    version_detail = await get_version(context, locale, version_id)
    file_detail = version_detail["file"]
    status = file_detail["status"]

    if status == "disabled":
        raise FatalSignatureError("XPI disabled on AMO")
    if status != "public":
        raise SignatureError("XPI not public")
    return file_detail["url"], file_detail["size"], file_detail["hash"]


async def get_version(context, locale, version_id):
    """Query AMO for the status of a given version for `locale`.

    `version_id` can be None, in which case the version is looked up by version
    number, raising FatalSignatureError if it can't be found.

    Returns the JSON response from AMO
    """
    locale_info = context.locales[locale]
    langpack_id = locale_info["id"]
    version = locale_info["version"]
    if version_id is None:
        # When the addon was already uploaded with this version we don't have
        # an id, and we can't look it up by version number
        # See https://github.com/mozilla/addons-server/issues/20388
        url = get_api_url(context, VERSION_LIST, id=langpack_id)
        addon_versions = await amo_get(context, url)
        for v in addon_versions["results"]:
            if v["version"] == version:
                return v
        # TODO: handle pagination?
        raise FatalSignatureError(f"could not find {langpack_id} version {version}")

    url = get_api_url(context, VERSION_DETAIL, id=langpack_id, version=version_id)
    return await amo_get(context, url)


async def get_signed_xpi(context, download_info, destination_path):
    """Download the signed xpi from AMO.

    Fetches from `download_path` (identified in a previous API call)
    And stores at `destination_path`.
    """
    download_path, download_size, download_hash = download_info
    with open(destination_path, "wb") as file:
        await amo_download(context, download_path, file)
    size = os.path.getsize(destination_path)
    if size != download_size:
        raise SignatureError(f"Wrong size for {download_path}, expected {download_size}, actual {size}")
    hashalg, amo_digest = download_hash.split(":", 1)
    with open(destination_path, "rb") as file:
        # XXX use hashlib.file_digest on python 3.11
        hash = hashlib.new(hashalg)
        buf = bytearray(2**18)
        view = memoryview(buf)
        while True:
            size = file.readinto(buf)
            if size == 0:
                break
            hash.update(view[:size])
        digest = hash.hexdigest()
    if digest != amo_digest:
        raise SignatureError(f"Wrong {hashalg} digest for {download_path}, expected {amo_digest}, actual {digest}")
