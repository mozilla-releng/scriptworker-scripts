import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from mozapkpublisher.huawei_api.auth import create_jwt, TOKEN_AUDIENCE


def _generate_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def test_create_jwt():
    private_pem, public_pem = _generate_keypair()

    before = int(time.time())
    token = create_jwt("my-key-id", "my-sub-account", private_pem)

    header = jwt.get_unverified_header(token)
    assert header["alg"] == "PS256"
    assert header["typ"] == "JWT"
    assert header["kid"] == "my-key-id"

    # Verifying with the public key proves it was signed with the private key.
    claims = jwt.decode(token, public_pem, algorithms=["PS256"], audience=TOKEN_AUDIENCE)
    assert claims["iss"] == "my-sub-account"
    assert claims["aud"] == TOKEN_AUDIENCE
    assert claims["exp"] - claims["iat"] == 3600
    assert claims["iat"] >= before
