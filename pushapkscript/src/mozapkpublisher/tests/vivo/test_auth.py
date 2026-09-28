import hashlib
import hmac
import time

import pytest

from mozapkpublisher.vivo_api.auth import (
    API_VERSION,
    RESPONSE_FORMAT_JSON,
    SIGN_METHOD_HMAC_SHA256,
    TARGET_APP_KEY_DEVELOPER,
    build_public_params,
    build_signed_params,
    build_string_to_sign,
    sign_params,
)

ACCESS_KEY = "an-access-key"
ACCESS_SECRET = "an-access-secret"


def test_build_public_params():
    before = int(time.time() * 1000)
    params = build_public_params("app.detail", ACCESS_KEY)

    assert params["method"] == "app.detail"
    assert params["access_key"] == ACCESS_KEY
    assert params["format"] == RESPONSE_FORMAT_JSON
    assert params["version"] == API_VERSION
    assert params["target_app_key"] == TARGET_APP_KEY_DEVELOPER
    assert params["sign_method"] == SIGN_METHOD_HMAC_SHA256
    # A millisecond timestamp, sent as a string.
    assert isinstance(params["timestamp"], str)
    assert int(params["timestamp"]) >= before


def test_build_string_to_sign_sorts_by_key():
    assert build_string_to_sign({"b": 2, "a": 1, "c": 3}) == "a=1&b=2&c=3"


def test_build_string_to_sign_sorts_in_ascii_order():
    """ASCII order, not a locale-aware or case-insensitive one: uppercase sorts before
    lowercase, which is what the gateway's own sort does."""
    assert build_string_to_sign({"packageName": "x", "access_key": "k", "Z": "z"}) == "Z=z&access_key=k&packageName=x"


def test_build_string_to_sign_drops_none_values():
    """An omitted optional parameter must be absent from the signature rather than signed
    as the string "None", or the signature won't match the request that is sent."""
    assert build_string_to_sign({"a": 1, "onlineTime": None, "b": 2}) == "a=1&b=2"


def test_build_string_to_sign_does_not_url_encode():
    """Values are signed raw even though they are percent-encoded in the request body.
    Signing the encoded form produces a signature the gateway rejects."""
    assert build_string_to_sign({"remark": "a b&c=d"}) == "remark=a b&c=d"


def test_sign_params_is_a_lowercase_hex_hmac_sha256():
    params = {"a": 1, "b": "two"}

    signature = sign_params(params, ACCESS_SECRET)

    expected = hmac.new(ACCESS_SECRET.encode("utf-8"), b"a=1&b=two", hashlib.sha256).hexdigest()
    assert signature == expected
    assert signature == signature.lower()
    assert len(signature) == 64


def test_build_signed_params_signs_public_and_biz_params():
    params = build_signed_params("app.upload.apk", ACCESS_KEY, ACCESS_SECRET, {"packageName": "org.mozilla.firefox"})

    assert params["packageName"] == "org.mozilla.firefox"
    assert params["method"] == "app.upload.apk"

    # `sign` cannot sign itself, so recomputing over everything else must reproduce it.
    signature = params.pop("sign")
    assert signature == sign_params(params, ACCESS_SECRET)


def test_build_signed_params_drops_none_biz_params():
    """A None biz parameter is left out of the request entirely, keeping it consistent
    with the signature, which also skips it."""
    params = build_signed_params("app.update.submit", ACCESS_KEY, ACCESS_SECRET, {"packageName": "a", "onlineTime": None})

    assert "onlineTime" not in params


@pytest.mark.parametrize("biz_params", (None, {}), ids=("none", "empty"))
def test_build_signed_params_without_biz_params(biz_params):
    params = build_signed_params("app.detail", ACCESS_KEY, ACCESS_SECRET, biz_params)

    signature = params.pop("sign")
    assert signature == sign_params(params, ACCESS_SECRET)
