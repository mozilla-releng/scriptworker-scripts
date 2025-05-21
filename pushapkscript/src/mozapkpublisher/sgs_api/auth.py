from typing import cast, List

import aiohttp
import jwt
import time
from .utils import raise_for_status_with_message


def create_jwt_for_auth(
    service_account_id: str, scopes: List[str], secret_key: str
) -> str:
    """
    Creates a JWT for use with `/auth/accessToken` according to
    https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/create-an-access-token.html#Create-a-JSON-Web-Token
    """
    return jwt.encode(
        {
            "iss": service_account_id,
            "scopes": scopes,
            "iat": time.time(),
            "exp": time.time() + 60,
        },
        secret_key,
        algorithm="RS256",
    )


async def create_access_token(jwt: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://devapi.samsungapps.com/auth/accessToken", headers=headers
        ) as resp:
            await raise_for_status_with_message(resp)

            result = await resp.json()

            return cast(str, result["createdItem"]["accessToken"])
