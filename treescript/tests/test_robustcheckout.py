"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = "8fd13d0bf74c40897812513babfc098b35c54c8725a8b744aae04a0df26a887caa09bd471dfcd0f142b0849ae9ed7de46fb4bf5fb491533890f68793b8faf135"

ROBUSTCHECKOUT_FILE = os.path.join(os.path.dirname(__file__), "..", "src", "treescript", "py2", "robustcheckout.py")


def test_robustcheckout_sha():
    hasher = hashlib.sha512()
    with open(ROBUSTCHECKOUT_FILE) as f:
        contents = f.read()
    hasher.update(contents.encode("utf-8"))
    assert hasher.hexdigest() == ROBUSTCHKOUT_SHA_512
