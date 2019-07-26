"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = (
    "0cea6b5b270740a0ec0b873de30494fbbb1e86d02e391ad8ee297fe9e414e6536fd5"
    "3d37130c31b05dd4994a4fa808c36ac3f5a5202d1474362866fde9be87aa"
)

ROBUSTCHECKOUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "src", "treescript", "py2", "robustcheckout.py"
)


def test_robustcheckout_sha():
    hasher = hashlib.sha512()
    with open(ROBUSTCHECKOUT_FILE) as f:
        contents = f.read()
    hasher.update(contents.encode("utf-8"))
    assert hasher.hexdigest() == ROBUSTCHKOUT_SHA_512
