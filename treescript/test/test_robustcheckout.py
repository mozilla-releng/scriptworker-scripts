"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = (
    '0b3b2d30a85fd9df8ce61db4d87ea710967f8e63a7ea1c3c4e023614467d646f'
    '09975b6dc069720d2f3cafb79d94c9f3e2d7d7048f22d063a7db06f94bc5ceb0'
)

ROBUSTCHECKOUT_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'py2', 'robustcheckout.py'
)


def test_robustcheckout_sha():
    hasher = hashlib.sha512()
    with open(ROBUSTCHECKOUT_FILE) as f:
        contents = f.read()
    hasher.update(contents.encode('utf-8'))
    assert hasher.hexdigest() == ROBUSTCHKOUT_SHA_512
