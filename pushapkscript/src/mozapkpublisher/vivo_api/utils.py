from typing import Any, Dict, Optional

import aiohttp

from mozapkpublisher.common.store_api import raise_for_status_with_message as _raise_for_status_with_message

from .error import VivoAuthenticationException, VivoAuthorizationException, VivoException, VivoUpdateException
from .result_codes import APP_STATE_FORBIDS_UPDATE, SUCCESS_CODE

# Reference document describing every interface and the codes it can return.
RESULT_CODES_DOC_URL = "https://developer.vivo.com/"


def _extract_error_message(body: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Dig the store's own error message out of a failed response.

    `subMsg` is preferred because on a business failure `msg` is the useless string
    "success" and `subMsg` carries the actual reason.
    """
    if isinstance(body, dict):
        return body.get("subMsg") or body.get("msg")
    return None


async def raise_for_status_with_message(resp: aiohttp.ClientResponse) -> None:
    """
    A wrapper around `raise_for_status` to show the error message returned by the vivo
    API when it's present.

    Note: this will exhaust the request body if it raises an exception
    """
    return await _raise_for_status_with_message(
        resp,
        extract_error_message=_extract_error_message,
        authentication_exception=VivoAuthenticationException,
        authorization_exception=VivoAuthorizationException,
    )


def unwrap_nested_envelope(body: dict) -> dict:
    """
    Return the envelope that actually carries the result.

    vivo's documented response is one envelope whose `data` is the payload. The sandbox
    gateway wraps that whole envelope inside another, so the payload lands at `data.data`
    and the per-call result code -- which is what reports whether the call worked -- at
    `data.code`. A `data` carrying a `code` is therefore unwrapped; no documented payload
    has a `code` of its own, and a failure has no `data` to look for beside it.
    """
    data = body.get("data")
    if isinstance(data, dict) and "code" in data:
        return data
    return body


def response_data(body: dict) -> Any:
    """
    Return the payload of a response, whichever envelope depth it arrived at.
    """
    return unwrap_nested_envelope(body).get("data")


def raise_for_response_code(body: dict) -> None:
    """
    Raise on an in-band failure, which vivo reports with an HTTP 200.

    Both envelopes are checked when the response is nested; see `unwrap_nested_envelope`
    for why the inner one carries a result that matters.
    """
    _raise_for_envelope(body)

    nested = unwrap_nested_envelope(body)
    if nested is not body:
        _raise_for_envelope(nested)


def _raise_for_envelope(body: dict) -> None:
    """
    Raise on a failure reported by a single envelope.

    The gateway-level `code` is checked first: when it fails there is no business result
    to inspect. Codes are compared as strings because the documented values are strings
    ("0", "23", "A0305"), and a missing level counts as passing.

    See `result_codes` for why a body claiming `"success": true` still has to be checked.
    """
    code = body.get("code")
    if code is not None and str(code) != SUCCESS_CODE:
        raise VivoException(
            "The vivo API rejected the request with code={}: {}. See {} for the documented result codes.".format(code, body.get("msg"), RESULT_CODES_DOC_URL)
        )

    sub_code = body.get("subCode")
    if sub_code is None or str(sub_code) == SUCCESS_CODE:
        return
    sub_code = str(sub_code)

    reason = APP_STATE_FORBIDS_UPDATE.get(sub_code)
    if reason is not None:
        raise VivoUpdateException(
            "The vivo app store refused the update because {} (subCode={}): {}. This has to be resolved in the "
            "vivo Developers console before a new release can be published.".format(reason, sub_code, body.get("subMsg"))
        )

    raise VivoException(
        "The vivo API returned subCode={}: {}. See {} for the documented result codes.".format(sub_code, body.get("subMsg"), RESULT_CODES_DOC_URL)
    )
