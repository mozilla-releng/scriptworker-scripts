import json
import time

import jwt

# Service Account JWTs are valid for one hour per Huawei's spec (exp = iat + 3600).
JWT_VALIDITY_SECONDS = 3600
# The `aud` claim must be exactly this value per the AppGallery Connect docs.
TOKEN_AUDIENCE = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"


def load_credentials(credentials_file: str) -> dict:
    """
    Load a Huawei AppGallery Connect Service Account credential file (the
    `*private.json` downloaded from the AppGallery Connect console when the Service
    Account is created). It contains `key_id`, `sub_account` and `private_key`.
    """
    with open(credentials_file) as fd:
        return json.load(fd)


def create_jwt(key_id: str, sub_account: str, private_key: str) -> str:
    """
    Create the self-signed JWT used as the bearer token for AppGallery Connect API
    requests in Service Account mode. The signed JWT *is* the access token -- there is
    no token-exchange step -- and it is valid for one hour, so it is regenerated for
    each batch of requests rather than cached/rotated externally.

    https://developer.huawei.com/consumer/en/doc/appgallery-connect-guides/agc-remoteconfig-getapicredentials-0000002539183415
    """
    now = int(time.time())
    return jwt.encode(
        {
            "aud": TOKEN_AUDIENCE,
            "iss": sub_account,
            "iat": now,
            "exp": now + JWT_VALIDITY_SECONDS,
        },
        private_key,
        algorithm="PS256",
        headers={"kid": key_id},
    )
