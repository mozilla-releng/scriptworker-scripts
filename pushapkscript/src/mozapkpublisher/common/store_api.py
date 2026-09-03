"""
Helpers shared between the async store API clients (Samsung Galaxy Store and
Huawei AppGallery). Both stores expose a similar shape: an aiohttp client that
issues authenticated requests, surfaces the store's own error message on failure,
and parses a JSON body. The store-specific bits (which header carries the account
id, how the error message is nested in the body, which exceptions to raise) are
passed in by the caller.
"""
import aiohttp
import json
from typing import Any, Awaitable, Callable, Dict, Optional, Type
from urllib.parse import urljoin


def build_apk_file_name(metadata: Dict[str, Any]) -> str:
    """
    Build a unique upload filename from APK metadata, shared across store
    integrations to avoid the "binary already in use" class of error (Bug 1974870).
    """
    return "{}-{}-{}.apk".format(
        metadata["package_name"], metadata["architecture"], metadata["version_name"]
    )


async def raise_for_status_with_message(
    resp: aiohttp.ClientResponse,
    *,
    extract_error_message: Callable[[Dict[str, Any]], Optional[str]],
    authentication_exception: Type[Exception],
    authorization_exception: Type[Exception],
) -> None:
    """
    A wrapper around `raise_for_status` that surfaces the error message returned by
    the store API when it's present. `extract_error_message(body)` returns the
    store-specific message (or None) dug out of the parsed JSON body.

    Note: this will exhaust the request body if it raises an exception.
    """
    if resp.ok:
        return None

    try:
        body = await resp.json()
    except (aiohttp.ContentTypeError, json.JSONDecodeError):
        # If the body isn't valid JSON, something went horribly wrong,
        # just defer the error reporting back to aiohttp.
        resp.raise_for_status()

    error_message = extract_error_message(body)
    if error_message is None:
        error_message = body.get("message", resp.reason) if isinstance(body, dict) else resp.reason

    if resp.status == 401:
        raise authentication_exception(error_message)
    elif resp.status == 403:
        raise authorization_exception(error_message)

    raise aiohttp.ClientResponseError(
        resp.request_info,
        resp.history,
        status=resp.status,
        message=error_message,
        headers=resp.headers,
    )


async def request(
    client: aiohttp.ClientSession,
    method: str,
    route: str,
    *,
    base_url: str,
    headers: Dict[str, str],
    raise_for_status: Callable[[aiohttp.ClientResponse], Awaitable[None]],
    raise_for_ret_code: Optional[Callable[[Dict[str, Any]], None]] = None,
    **kwargs: Any,
) -> Any:
    """
    The shared body of each store client's `_request`: resolve the URL, issue the request
    with the store's headers, surface the store's error message on failure, parse the
    JSON body, and -- for stores that wrap responses in an in-band envelope -- run an
    optional in-band error check.

    `raise_for_status` and `raise_for_ret_code` are the store's own error handlers; the
    latter is omitted by stores (e.g. Samsung) that report all errors via HTTP status.
    """
    url = urljoin(base_url, route)
    response = await client.request(method, url, headers=headers, **kwargs)
    await raise_for_status(response)
    body = await response.json()
    if raise_for_ret_code is not None and isinstance(body, dict):
        raise_for_ret_code(body)
    return body
