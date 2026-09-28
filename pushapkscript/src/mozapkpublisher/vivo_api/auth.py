"""
Request signing for the vivo Developers Open API.

The gateway authenticates every call by a `sign` parameter carried in the request body
rather than by a header or a bearer token, so there is no token to fetch, cache or
rotate: each request is signed from the access key/secret pair on its own.

See "vivo Developers Open API Service Documentation", sections "Usage Guide" and
"Examples of Calling Methods in Java", at https://developer.vivo.com/
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional

# The gateway accepts "hmac-sha256" and "md5" for `sign_method`; only HMAC-SHA256, the
# one vivo's own example uses, is implemented.
SIGN_METHOD_HMAC_SHA256 = "hmac-sha256"

# `target_app_key` names the service being addressed. "developer" is the publishing API.
TARGET_APP_KEY_DEVELOPER = "developer"

# `version` is the Open API version and `format` the response encoding. These are the
# documented defaults and the only published values.
API_VERSION = "1.0"
RESPONSE_FORMAT_JSON = "json"


def build_public_params(method: str, access_key: str) -> Dict[str, Any]:
    """
    Build the public request parameters every interface requires. `timestamp` is in
    milliseconds.
    """
    return {
        "method": method,
        "access_key": access_key,
        "timestamp": str(int(time.time() * 1000)),
        "format": RESPONSE_FORMAT_JSON,
        "version": API_VERSION,
        "target_app_key": TARGET_APP_KEY_DEVELOPER,
        "sign_method": SIGN_METHOD_HMAC_SHA256,
    }


def build_string_to_sign(params: Dict[str, Any]) -> str:
    """
    Build the string the signature is computed over: every parameter sorted by key in
    ASCII order, rendered as `key=value` and joined with `&`.

    Values are signed raw: signing the percent-encoded form the request body carries
    produces a signature the gateway rejects. None-valued parameters are dropped rather
    than signed as "None", so an omitted optional parameter is absent from both the
    signature and the request.
    """
    return "&".join("{}={}".format(key, params[key]) for key in sorted(params) if params[key] is not None)


def sign_params(params: Dict[str, Any], access_secret: str) -> str:
    """
    Sign the given parameters with the access secret, returning the lowercase hex
    digest the gateway expects.
    """
    return hmac.new(
        access_secret.encode("utf-8"),
        build_string_to_sign(params).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_signed_params(
    method: str,
    access_key: str,
    access_secret: str,
    biz_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the full parameter set for a call: the public parameters, the interface's own
    ("biz") parameters, and the `sign` computed over both.

    `sign` is added last because it cannot sign itself. A file being uploaded is never
    passed in here: its bytes are not a signable parameter value and the gateway
    excludes it from the signature.
    """
    params = build_public_params(method, access_key)
    if biz_params:
        params.update({key: value for key, value in biz_params.items() if value is not None})
    params["sign"] = sign_params(params, access_secret)
    return params
