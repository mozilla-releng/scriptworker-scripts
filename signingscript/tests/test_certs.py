import glob
import pathlib
import pytest
import signingscript

CERT_DIR = pathlib.Path(signingscript.__file__).parent / "data"


@pytest.mark.parametrize(
    "cert",
    glob.glob(f"{CERT_DIR}/authenticode*"),
)
def test_authenticode_cert_line_endings(cert):
    with open(cert, "rb") as f:
        contents = f.read()
        if b"\r\n" in contents:
            assert False, f"{cert} contains CRLF line endings; must be LF only"
