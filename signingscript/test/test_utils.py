from signingscript.utils import get_detached_signatures


def test_detached_signatures():
    assert get_detached_signatures(["mar", "gpg", "pgp"]) == [("gpg", ".asc", "text/plain")]
