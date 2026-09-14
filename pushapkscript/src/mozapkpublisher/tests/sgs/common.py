def basic_auth_headers():
    headers = {
        "service-account-id": "service_account_id",
        "Authorization": "Bearer access_token",
        "User-Agent": "mozapkpublisher",
    }
    return headers
