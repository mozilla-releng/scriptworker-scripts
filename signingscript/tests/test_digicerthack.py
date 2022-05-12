import hashlib
import tempfile
from pathlib import Path

import pytest
from conftest import TEST_DATA_DIR

from signingscript import digicerthack

CA_PATH = "/usr/lib/ssl/certs/ca-certificates.crt"


@pytest.mark.parametrize(
    "signed,expected",
    (
        # Firefox 100.0 stub installer; new timestamp chain, missing cross cert
        ("stub-100.exe", "2349fd12894f4f92905b760568746d7f0f9030c2888201d4fadeddd95d8e0acb"),
        # Firefox 98.0 stub installer; old timestamp chain, no change necessary
        ("stub-98.exe", "dbd023ecb77368bdaecc6952826063fee317294d4993c30478c33386d6d539f9"),
    ),
)
def test_digicerthack(signed, expected):
    signed_file = Path(TEST_DATA_DIR) / signed
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        mangled = tmpdir / "mangled.exe"
        digicerthack.add_cert_to_signed_file(signed_file, mangled, CA_PATH, CA_PATH)
        assert mangled.exists()
        assert hashlib.sha256(mangled.read_bytes()).hexdigest() == expected
        mangled_twice = tmpdir / "mangledtwice.exe"
        digicerthack.add_cert_to_signed_file(mangled, mangled_twice, CA_PATH, CA_PATH)
        assert mangled_twice.exists()
        assert hashlib.sha256(mangled_twice.read_bytes()).hexdigest() == expected
