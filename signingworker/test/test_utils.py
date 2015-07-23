from unittest import TestCase
from signingworker.utils import get_detached_signatures


class TestDetachedSignatures(TestCase):
    def test_detached_signatures(self):
        self.assertEqual(
            get_detached_signatures(["mar", "gpg", "pgp"]),
            [("gpg", ".asc")]
        )
