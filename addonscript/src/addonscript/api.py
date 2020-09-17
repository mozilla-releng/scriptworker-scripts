"""API helpers for addonscript."""

from aiohttp.client_exceptions import ClientResponseError

from addonscript.exceptions import AMOConflictError, AuthFailedError, AuthInsufficientPermissionsError, FatalSignatureError, SignatureError
from addonscript.task import get_channel
from addonscript.utils import amo_download, amo_get, amo_put, get_api_url

# https://addons-server.readthedocs.io/en/latest/topics/api/signing.html#uploading-a-version
UPLOAD_VERSION = "api/v3/addons/{id}/versions/{version}/"

# https://addons-server.readthedocs.io/en/latest/topics/api/signing.html#checking-the-status-of-your-upload
UPLOAD_STATUS = "api/v3/addons/{id}/versions/{version}/"
UPLOAD_STATUS_PK = "api/v3/addons/{id}/versions/{version}/uploads/{upload_pk}/"


# https://addons-server.readthedocs.io/en/latest/topics/api/applications.html
# XXX when we want to support multiple products, we'll need to unhardcode the
#     `firefox` below
ADD_VERSION = "api/v4/applications/firefox/{version}/"


async def add_version(context, version):
    """Add a new version to AMO.

    Use the `min_version` here, rather than the string with the buildid etc.

    Raises:
        BadVersionError: If the XPI's version fails to sanity check against AMO


    """
    url = get_api_url(context, ADD_VERSION, version=version)

    try:
        await amo_put(context, url, data=None)
    except ClientResponseError as exc:
        if exc.status == 401:
            raise AuthFailedError("Addonscript credentials are misconfigured")
        elif exc.status == 403:
            raise AuthInsufficientPermissionsError("Addonscript creds are missing permissions")
        raise exc


async def do_upload(context, locale):
    """Upload the language pack for `locale` to AMO.

    Returns the JSON response from AMO
    """
    locale_info = context.locales[locale]
    langpack_id = locale_info["id"]
    version = locale_info["version"]
    url = get_api_url(context, UPLOAD_VERSION, id=langpack_id, version=version)
    with open(context.locales[locale]["unsigned"], "rb") as file:
        data = {"channel": get_channel(context.task), "upload": file}
        try:
            result = await amo_put(context, url, data)
        except ClientResponseError as exc:
            # XXX: .code is deprecated in aiohttp 3.1 in favor of .status
            if exc.status == 409:
                raise AMOConflictError("Addon <{}> already present on AMO with version <{}>".format(langpack_id, version))
            # If response code is not 409 - CONFLICT, bubble the exception
            raise exc
        return result


async def get_signed_addon_url(context, locale, pk):
    """Query AMO to get the location of the signed XPI.

    This function should be called within `scriptworker.utils.retry_async()`.

    Raises:
        SignatureError: If the metadata lacks something or if the server-side Automated validation
        reported something. This is a retryable exception.
        FatalSignatureError: if there is a nonrecoverable error from this submission, e.g. validation errors.
        aiohttp.ClientError: If there is some sort of networking issue.
        asyncio.TimeoutError: If the network request times out.

    Returns the signed XPI URL

    """
    # XXX Retry is done at top-level. Avoiding a retry here avoids never-ending retries cascade
    upload_status = await get_upload_status(context, locale, pk)

    if len(upload_status["files"]) != 1:
        raise SignatureError("Expected 1 file. Got ({}) full response: {}".format(len(upload_status["files"]), upload_status))

    if upload_status.get("validation_results"):
        validation_errors = upload_status["validation_results"].get("errors")
        if validation_errors:
            raise FatalSignatureError("Automated validation produced errors: {}".format(validation_errors))

    signed_data = upload_status["files"][0]

    if not signed_data.get("signed"):
        raise SignatureError('Expected XPI "signed" parameter. Got: {}'.format(signed_data))

    if not signed_data.get("download_url"):
        raise SignatureError('Expected XPI "download_url" parameter. Got: {}'.format(signed_data))

    return signed_data["download_url"]


async def get_upload_status(context, locale, upload_pk):
    """Query AMO for the status of a given upload for `locale`.

    Returns the JSON response from AMO
    """
    locale_info = context.locales[locale]
    langpack_id = locale_info["id"]
    version = locale_info["version"]
    if upload_pk:
        format_string = UPLOAD_STATUS_PK
    else:
        # When the addon was already uploaded with this version we don't have
        # an upload_pk
        format_string = UPLOAD_STATUS
    url = get_api_url(context, format_string, id=langpack_id, version=version, upload_pk=upload_pk)
    return await amo_get(context, url)


async def get_signed_xpi(context, download_path, destination_path):
    """Download the signed xpi from AMO.

    Fetches from `download_path` (identified in a previous API call)
    And stores at `destination_path`.
    """
    with open(destination_path, "wb") as file:
        await amo_download(context, download_path, file)
