"""Common utilities for addonscript."""

import time
from uuid import uuid4

from jose import jws
from async_timeout import timeout


def generate_JWT(context, _iat=None):
    """Create and Sign a JWT valid for AMO HTTP requests.

    Uses context.config 'jwt_user' and 'jwt_secret' and sets an expiration of
    4 minutes (AMO supports a max of 5)
    """
    user = context.config['jwt_user']
    secret = context.config['jwt_secret']
    jti = str(uuid4())
    iat = _iat or int(time.time())  # _iat for testing sanity
    exp = iat + 60*4  # AMO has a 5 minute max, so set this to 4 minutes after issued
    payload = {
        'iss': user,
        'jti': jti,
        'iat': iat,
        'exp': exp,
    }
    token_str = jws.sign(payload, secret, algorithm='HS256')
    return token_str


async def amo_get(context, url):
    """Perform a GET request against AMO's API.

    Automatically fills in the HTTP header with the Authorization token.
    Assumes request will return a valid json object, on success.
    """
    async with timeout(30):
        resp = context.session.get(
            url, headers={
                'Authorization': 'JWT {}'.format(generate_JWT(context))
                },
            )
        async with resp as r:
            r.raise_for_status()
            return await r.json()


async def amo_download(context, url, file):
    """Perform a download request via AMO's API.

    Automatically fills in the HTTP header with the Authorization token.
    Saves the file at `url` to `file`
    """
    async with timeout(60):
        resp = context.session.get(
            url, headers={
                'Authorization': 'JWT {}'.format(generate_JWT(context))
                },
            )
        async with resp as r:
            r.raise_for_status()
            file.write(await r.read())


async def amo_put(context, url, data):
    """Perform a PUT request against AMO's API.

    Automatically fills in the HTTP header with the Authorization token.
    Passes values in the `data` dictionary as FORM data.
    Assumes request will return a valid json object, on success.
    """
    async with timeout(270):  # 4 minutes, 30 sec.
        resp = context.session.put(
            url, headers={
                'Authorization': 'JWT {}'.format(generate_JWT(context))
                },
            data=data,
            )
        async with resp as r:
            r.raise_for_status()
            return await r.json()


def get_api_url(context, path, **kwargs):
    """Return an AMO api url, given path and arguments.

    Uses `context.config['amo_server'] to populate the hostname, followed by `path`
    Calls str.format() on the path with arguments in kwargs.
    """
    server = context.config['amo_server']
    if '{' in path:
        path = path.format(**kwargs)
    return "{}/{}".format(server, path)
