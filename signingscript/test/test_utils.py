from unittest import TestCase
from signingscript.utils import get_detached_signatures


class TestDetachedSignatures(TestCase):
    def test_detached_signatures(self):
        self.assertEqual(
            get_detached_signatures(["mar", "gpg", "pgp"]),
            [("gpg", ".asc", "text/plain")]
        )
