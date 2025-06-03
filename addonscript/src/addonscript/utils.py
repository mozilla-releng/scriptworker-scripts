"""Common utilities for addonscript."""

import logging
import time
from uuid import uuid4

import jwt
from async_timeout import timeout

from addonscript.task import get_amo_instance_config_from_scope

log = logging.getLogger(__name__)


def generate_JWT(context):
    """Create and Sign a JWT valid for AMO HTTP requests.

    Uses context.config 'jwt_user' and 'jwt_secret' and sets an expiration of
    4 minutes (AMO supports a max of 5)
    """
    amo_instance = get_amo_instance_config_from_scope(context)
    user = amo_instance["jwt_user"]
    secret = amo_instance["jwt_secret"]
    jti = str(uuid4())
    iat = int(time.time())
    exp = iat + 60 * 4  # AMO has a 5 minute max, so set this to 4 minutes after issued
    payload = {"iss": user, "jti": jti, "iat": iat, "exp": exp}
    token_str = jwt.encode(payload, secret, algorithm="HS256")
    return token_str


async def amo_get(context, url):
    """Perform a GET request against AMO's API.

    Automatically fills in the HTTP header with the Authorization token.
    Assumes request will return a valid json object.
    """
    log.debug('Calling amo_get() with URL "{}"'.format(url))
    async with timeout(30):
        resp = context.session.get(url, headers={"Authorization": "JWT {}".format(generate_JWT(context))})
        async with resp as r:
            log.debug('amo_get() for URL "{}" returned HTTP status code: {}'.format(url, r.status))
            returned_value = await r.json()
            log.debug('amo_get() for URL "{}" returned: {}'.format(url, returned_value))
            r.raise_for_status()
            return returned_value


async def amo_download(context, url, file):
    """Perform a download request via AMO's API.

    Automatically fills in the HTTP header with the Authorization token.
    Saves the file at `url` to `file`
    """
    log.debug('Calling amo_download() with URL "{}"'.format(url))
    async with timeout(60):
        resp = context.session.get(url, headers={"Authorization": "JWT {}".format(generate_JWT(context))})
        async with resp as r:
            log.debug('amo_download() for URL "{}" returned HTTP status code: {}'.format(url, r.status))
            r.raise_for_status()
            log.debug('Writing content at URL "{}" to file "{}"'.format(url, file.name))
            file.write(await r.read())


async def amo_put(context, url, data=None, json=None):
    """Perform a PUT request against AMO's API.

    Automatically fills in the HTTP header with the Authorization token.
    Passes values in the `data` dictionary as FORM data.
    Assumes request will return a valid json object.
    """
    log.debug('Calling amo_put() with URL "{}"'.format(url))
    async with timeout(270):  # 4 minutes, 30 sec.
        resp = context.session.put(url, headers={"Authorization": "JWT {}".format(generate_JWT(context))}, data=data, json=json)
        async with resp as r:
            log.debug('amo_put() for URL "{}" returned HTTP status code: {}'.format(url, r.status))
            # we silence aiohttp in case we have Null returns from AMO API
            returned_value = await r.json(content_type=None)
            log.debug('amo_put() for URL "{}" returned: {}'.format(url, returned_value))
            r.raise_for_status()
            return returned_value


async def amo_post(context, url, data=None, json=None):
    """Perform a POST request against AMO's API.

    Automatically fills in the HTTP header with the Authorization token.
    Passes values in the `data` dictionary as FORM data.
    Assumes request will return a valid json object.
    """
    log.debug('Calling amo_post() with URL "{}"'.format(url))
    async with timeout(270):  # 4 minutes, 30 sec.
        resp = context.session.post(url, headers={"Authorization": "JWT {}".format(generate_JWT(context))}, data=data, json=json)
        async with resp as r:
            log.debug('amo_post() for URL "{}" returned HTTP status code: {}'.format(url, r.status))
            r.raise_for_status()
            # we silence aiohttp in case we have Null returns from AMO API
            returned_value = await r.json(content_type=None)
            log.debug('amo_post() for URL "{}" returned: {}'.format(url, returned_value))
            return returned_value


def get_api_url(context, path, **kwargs):
    """Return an AMO api url, given path and arguments.

    Uses `context.config['amo_server'] to populate the hostname, followed by `path`
    Calls str.format() on the path with arguments in kwargs.
    """
    amo_instance = get_amo_instance_config_from_scope(context)
    server = amo_instance["amo_server"]
    if "{" in path:
        path = path.format(**kwargs)
    return "{}/{}".format(server, path)
