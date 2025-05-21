import aiohttp
import json
from .error import SgsAuthenticationException, SgsAuthorizationException


async def raise_for_status_with_message(resp: aiohttp.ClientResponse) -> None:
    """
    A wrapper around `raise_for_status` to show the error message returned by the
    samsung API when it's present.

    Note: this will exhaust the request body if it raises an exception
    """
    if resp.ok:
        return None

    try:
        body = await resp.json()
    except (aiohttp.ContentTypeError, json.JSONDecodeError):
        # If the body isn't valid JSON, something went horribly wrong,
        # just defer the error reporting back to aiohttp.
        resp.raise_for_status()

    error_message = None
    if "body" in body:
        error_message = body["body"].get("errorMsg")

    if error_message is None:
        error_message = body.get("message", resp.reason)

    if resp.status == 401:
        raise SgsAuthenticationException(error_message)
    elif resp.status == 403:
        raise SgsAuthorizationException(error_message)

    raise aiohttp.ClientResponseError(
        resp.request_info,
        resp.history,
        status=resp.status,
        message=error_message,
        headers=resp.headers,
    )
