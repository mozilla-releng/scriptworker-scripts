import hashlib
from urllib.parse import urljoin

import mozapkpublisher.vivo_api as vivo_api

# Derived from the client's own constants;
# `test_the_production_gateway_is_not_left_pointing_at_a_test_route` pins their real values.
ROUTER_URL = urljoin(vivo_api.BASE_URL, vivo_api.ROUTER_ROUTE)

# The public parameters every signed request carries, plus the signature itself.
# `timestamp` and `sign` are not asserted on directly: the first is wall-clock and the
# second derives from it. `test_auth` covers the signature algorithm instead.
PUBLIC_PARAM_NAMES = frozenset(
    {"method", "access_key", "timestamp", "format", "version", "target_app_key", "sign_method", "sign"}
)


def basic_headers():
    return {"User-Agent": "mozapkpublisher"}


def form_fields(form):
    """Flatten an `aiohttp.FormData` into `{field name: (filename, value)}`.

    `_fields` is private, but it is the only way to see what a multipart upload
    actually carries; asserting `data=ANY` instead would let the signed parameters and
    the per-APK filename regress silently.
    """
    return {type_options["name"]: (type_options.get("filename"), value) for type_options, _headers, value in form._fields}


def recorded_calls(responses_mock, method="POST"):
    """Every recorded request `responses_mock` saw for the gateway route."""
    return [
        call
        for (recorded_method, recorded_url), calls in responses_mock.requests.items()
        for call in calls
        if recorded_method == method and str(recorded_url) == ROUTER_URL
    ]


def posted_params(responses_mock):
    """The parameters of the one urlencoded request sent to the gateway."""
    calls = recorded_calls(responses_mock)
    assert len(calls) == 1, "expected exactly one request, got {}".format(len(calls))
    return calls[0].kwargs["data"]


def posted_upload_fields(responses_mock):
    """The multipart fields of the one upload request sent to the gateway."""
    calls = recorded_calls(responses_mock)
    assert len(calls) == 1, "expected exactly one request, got {}".format(len(calls))
    return form_fields(calls[0].kwargs["data"])


def business_failure(sub_code, sub_msg):
    """A body the way vivo reports a *business* failure: HTTP 200, a successful gateway
    `code`, `"success": true`, and the real reason hidden in `subCode`/`subMsg`."""
    return {"data": None, "code": "0", "msg": "success", "subCode": sub_code, "subMsg": sub_msg, "success": True}


def app_detail(**overrides):
    """An `app.detail` payload carrying everything `app.update.basic.info` needs."""
    data = {
        "packageName": "org.mozilla.firefox",
        "languageCodes": ["en_in", "ms"],
        "nationCodes": ["in", "id"],
        "email": "release@mozilla.com",
        "categoryId": 80000006,
        "website": "https://mozilla.org",
        "phone": "1234567890",
        "iarc": 12,
        "privacyStatement": "https://mozilla.org/privacy",
        "versionCode": 100,
        "status": 2,
    }
    # An override of None removes the key, which is how a store that reports nothing for
    # a field is modelled.
    for key, value in overrides.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return success(data)


def success(data=None):
    return {"data": data, "code": "0", "msg": "success", "subCode": "0", "subMsg": "success", "success": True}


def upload_success(apk_path, package_name="org.mozilla.firefox"):
    """The `app.upload.apk` response for a given file, echoing the MD5 vivo computed."""
    with open(apk_path, "rb") as fh:
        file_md5 = hashlib.md5(fh.read()).hexdigest()
    return success({"packageName": package_name, "fileMd5": file_md5, "serialNumber": "serial-1", "versionCode": 100, "versionName": "116.0"})


def register_publish_flow(responses_mock, apk_path, submit=True):
    """Queue the responses for a full publish: app.detail -> upload -> bind -> submit.

    `app.detail` comes first because the basic-info record is resolved before the upload,
    so a gap costs a round trip rather than a multi-hundred-megabyte upload.
    """
    responses_mock.post(ROUTER_URL, payload=app_detail())
    responses_mock.post(ROUTER_URL, payload=upload_success(apk_path))
    responses_mock.post(ROUTER_URL, payload=success())
    if submit:
        responses_mock.post(ROUTER_URL, payload=success())
