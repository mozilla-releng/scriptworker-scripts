from aiohttp import ClientResponseError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

import jwt
import pytest
import time
from contextlib import nullcontext as does_not_raise

from .common import basic_auth_headers
from mozapkpublisher.sgs_api.auth import create_jwt_for_auth, create_access_token
from mozapkpublisher.sgs_api.error import (
    SgsAuthenticationException,
    SgsAuthorizationException,
)


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=1024, backend=default_backend()
    )
    public_key = private_key.public_key()

    return public_key, private_key


def test_create_jwt(rsa_keypair):
    public_key, private_key = rsa_keypair

    token = create_jwt_for_auth("abc-123", ["publishing"], private_key)
    decoded_token = jwt.decode(token, public_key, algorithms=["RS256"])
    assert decoded_token["iss"] == "abc-123"
    assert decoded_token["scopes"] == ["publishing"]
    assert decoded_token["exp"] > time.time() > decoded_token["iat"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            200,
            {"ok": True, "createdItem": {"accessToken": "jambonBeurre"}},
            does_not_raise(),
        ),
        pytest.param(
            401,
            {
                "code": "AUTH_REQUIRE",
                "message": "Not found serviceAccount by serviceAccountId",
                "from": "asgw",
            },
            pytest.raises(SgsAuthenticationException, match="Not found serviceAccount"),
        ),
        pytest.param(
            403,
            {"code": "NO_PERMISSION", "message": "Insufficient scopes", "from": "asgw"},
            pytest.raises(SgsAuthorizationException, match="Insufficient scopes"),
        ),
        pytest.param(
            500,
            {"message": "invalid signature"},
            pytest.raises(ClientResponseError, match="invalid signature"),
        ),  # The API returns this when the JWT is badly encoded, make sure we handle this properly
    ),
)
async def test_create_token(rsa_keypair, status, response, expectation, responses_mock):
    public_key, private_key = rsa_keypair

    jwt = create_jwt_for_auth("abc-123", ["publishing"], private_key)
    responses_mock.post(
        "https://devapi.samsungapps.com/auth/accessToken",
        status=status,
        payload=response,
    )
    with expectation as exc:
        token = await create_access_token(jwt)

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/auth/accessToken",
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {jwt}"},
    )

    if exc is None:
        assert token == "jambonBeurre"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            401,
            {"code": "AUTH_REQUIRE", "message": "Invalid accessToken", "from": "asgw"},
            pytest.raises(SgsAuthenticationException, match="Invalid accessToken"),
        ),
        pytest.param(
            401,
            {
                "code": "AUTH_REQUIRE",
                "message": "Not found serviceAccount by serviceAccountId",
                "from": "asgw",
            },
            pytest.raises(SgsAuthenticationException, match="Not found serviceAccount"),
        ),
        pytest.param(200, {"ok": True}, does_not_raise()),
    ),
)
async def test_check_token(sgs, status, response, expectation, responses_mock):
    responses_mock.get(
        "https://devapi.samsungapps.com/auth/checkAccessToken",
        status=status,
        payload=response,
    )

    with expectation as exc:
        body = await sgs.check_access_token()

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/auth/checkAccessToken",
        method="GET",
        headers=basic_auth_headers(),
    )

    if exc is None:
        assert body == {"ok": True}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            401,
            {"code": "AUTH_REQUIRE", "message": "Invalid accessToken", "from": "asgw"},
            pytest.raises(SgsAuthenticationException, match="Invalid accessToken"),
        ),
        pytest.param(
            401,
            {
                "code": "AUTH_REQUIRE",
                "message": "Not found serviceAccount by serviceAccountId",
                "from": "asgw",
            },
            pytest.raises(SgsAuthenticationException, match="Not found serviceAccount"),
        ),
        pytest.param(200, {"ok": True}, does_not_raise()),
    ),
)
async def test_revoke_token(sgs, status, response, expectation, responses_mock):
    responses_mock.delete(
        "https://devapi.samsungapps.com/auth/revokeAccessToken",
        status=status,
        payload=response,
    )

    with expectation as exc:
        body = await sgs.revoke_access_token()

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/auth/revokeAccessToken",
        method="DELETE",
        headers=basic_auth_headers(),
    )

    if exc is None:
        assert body == {"ok": True}
