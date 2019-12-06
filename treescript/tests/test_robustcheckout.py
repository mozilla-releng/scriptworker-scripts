"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = "93da691b777abaa4e8f8db9eb130daf081412709db3ffa05aba80bb05d7e17b0157db824ead65f4af73b48951e1030a95706b8aabe1eed06483c0ed9239d8592"

ROBUSTCHECKOUT_FILE = os.path.join(os.path.dirname(__file__), "..", "src", "treescript", "py2", "robustcheckout.py")


def test_robustcheckout_sha():
    hasher = hashlib.sha512()
    with open(ROBUSTCHECKOUT_FILE) as f:
        contents = f.read()
    hasher.update(contents.encode("utf-8"))
    assert hasher.hexdigest() == ROBUSTCHKOUT_SHA_512
