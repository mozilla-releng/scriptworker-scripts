def basic_auth_headers():
    headers = {
        "Authorization": "Bearer jwt-token",
        "User-Agent": "mozapkpublisher",
    }
    return headers


def form_fields(form):
    """Flatten an `aiohttp.FormData` into `{field name: (filename, value)}`.

    `_fields` is private, but it is the only way to see what a multipart upload
    actually carries; asserting `data=ANY` instead would let the authCode and the
    per-APK filename regress silently.
    """
    return {
        type_options["name"]: (type_options.get("filename"), value)
        for type_options, _headers, value in form._fields
    }


def recorded_calls(responses_mock, method, url):
    """Every recorded request `responses_mock` saw for `method` and `url`."""
    return [
        call
        for (recorded_method, recorded_url), calls in responses_mock.requests.items()
        for call in calls
        if recorded_method == method and str(recorded_url) == url
    ]
