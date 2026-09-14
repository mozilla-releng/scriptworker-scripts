import aiohttp
from typing import Any, Dict, Optional
from mozapkpublisher.common.store_api import raise_for_status_with_message as _raise_for_status_with_message
from .error import (
    HuaweiAuthenticationException,
    HuaweiAuthorizationException,
    HuaweiException,
)


# Reference page listing every documented `ret.code` the publishing API can return.
RESULT_CODES_DOC_URL = "https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-publishingapi-errorcode-0000001163523297"


def _extract_error_message(body: Optional[Dict[str, Any]]) -> Optional[str]:
    if isinstance(body, dict) and "ret" in body:
        return body["ret"].get("msg")
    return None


async def raise_for_status_with_message(resp: aiohttp.ClientResponse) -> None:
    """
    A wrapper around `raise_for_status` to show the error message returned by the
    huawei API when it's present.

    Note: this will exhaust the request body if it raises an exception
    """
    return await _raise_for_status_with_message(
        resp,
        extract_error_message=_extract_error_message,
        authentication_exception=HuaweiAuthenticationException,
        authorization_exception=HuaweiAuthorizationException,
    )


def raise_for_ret_code(body: dict) -> None:
    """
    Huawei wraps responses in a `ret` envelope (`{ret: {code: int, msg: str}, ...}`).
    A non-zero `code` indicates an in-band failure even when the HTTP status is 200.

    The full list of documented `ret.code` values is at `RESULT_CODES_DOC_URL`.
    """
    ret = body.get("ret")
    if not ret:
        return
    code = ret.get("code")
    if code in (None, 0):
        return
    raise HuaweiException(
        "Huawei API returned ret.code={}: {}. See {} for the list of result codes.".format(
            code, ret.get("msg"), RESULT_CODES_DOC_URL
        )
    )
