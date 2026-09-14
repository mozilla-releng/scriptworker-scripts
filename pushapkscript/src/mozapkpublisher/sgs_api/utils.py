import aiohttp
from typing import Any, Dict, Optional
from mozapkpublisher.common.store_api import raise_for_status_with_message as _raise_for_status_with_message
from .error import SgsAuthenticationException, SgsAuthorizationException


def _extract_error_message(body: Dict[str, Any]) -> Optional[str]:
    if "body" in body:
        return body["body"].get("errorMsg")
    return None


async def raise_for_status_with_message(resp: aiohttp.ClientResponse) -> None:
    """
    A wrapper around `raise_for_status` to show the error message returned by the
    samsung API when it's present.

    Note: this will exhaust the request body if it raises an exception
    """
    return await _raise_for_status_with_message(
        resp,
        extract_error_message=_extract_error_message,
        authentication_exception=SgsAuthenticationException,
        authorization_exception=SgsAuthorizationException,
    )
