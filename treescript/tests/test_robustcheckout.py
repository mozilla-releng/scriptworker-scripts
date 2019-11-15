"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = "29f9ddf3a7fc86ef4ded8fce4f2759e17da580e71e77c87857bcab346db5bfa7adb0cba74a09954fe9ffdba33b5c27a8a2c07f84ff1713d7700118c234223f49"

ROBUSTCHECKOUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "src", "treescript", "py2", "robustcheckout.py"
)


def test_robustcheckout_sha():
    hasher = hashlib.sha512()
    with open(ROBUSTCHECKOUT_FILE) as f:
        contents = f.read()
    hasher.update(contents.encode("utf-8"))
    assert hasher.hexdigest() == ROBUSTCHKOUT_SHA_512
