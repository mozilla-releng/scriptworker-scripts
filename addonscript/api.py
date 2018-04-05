"""API helpers for addonscript."""

from addonscript.utils import get_api_url, amo_put, amo_get, amo_download
from addonscript.task import get_channel

# https://addons-server.readthedocs.io/en/latest/topics/api/signing.html#uploading-a-version
UPLOAD_VERSION = "api/v3/addons/{id}/versions/{version}/"

# https://addons-server.readthedocs.io/en/latest/topics/api/signing.html#checking-the-status-of-your-upload
UPLOAD_STATUS = "api/v3/addons/{id}/versions/{version}/uploads/{upload_pk}/"


async def do_upload(context, locale):
    """Upload the language pack for `locale` to AMO.

    Returns the JSON response from AMO
    """
    locale_info = context.locales[locale]
    langpack_id = locale_info['id']
    version = locale_info['version']
    url = get_api_url(context, UPLOAD_VERSION, id=langpack_id, version=version)
    with open(context.locales[locale]['unsigned'], 'rb') as file:
        data = {
            'channel': get_channel(context.task),
            'upload': file,
        }
        return await amo_put(context, url, data)


async def get_upload_status(context, locale, upload_pk):
    """Query AMO for the status of a given upload for `locale`.

    Returns the JSON response from AMO
    """
    locale_info = context.locales[locale]
    langpack_id = locale_info['id']
    version = locale_info['version']
    url = get_api_url(context, UPLOAD_STATUS, id=langpack_id, version=version,
                      upload_pk=upload_pk)
    return await amo_get(context, url)


async def get_signed_xpi(context, download_path, destination_path):
    """Download the signed xpi from AMO.

    Fetches from `download_path` (identified in a previous API call)
    And stores at `destination_path`.
    """
    with open(destination_path, 'wb') as file:
        await amo_download(context, download_path, file)
