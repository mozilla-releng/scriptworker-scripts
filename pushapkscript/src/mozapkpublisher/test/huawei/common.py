def basic_auth_headers():
    headers = {
        "Authorization": "Bearer jwt-token",
        "User-Agent": "mozapkpublisher",
    }
    return headers
