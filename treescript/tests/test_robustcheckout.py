"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = "194825d13ba83190ce2e1ff1e4842105562f264e1459d4dbe5d42eb6edf228c71f9f2e19cd34d75150db5513eb625c97304d1e36d2baf3e2d79cd9748bd9d3ac"

ROBUSTCHECKOUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "src", "treescript", "py2", "robustcheckout.py"
)


def test_robustcheckout_sha():
    hasher = hashlib.sha512()
    with open(ROBUSTCHECKOUT_FILE) as f:
        contents = f.read()
    hasher.update(contents.encode("utf-8"))
    assert hasher.hexdigest() == ROBUSTCHKOUT_SHA_512
