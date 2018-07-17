"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = (
    '4c4f866cdc026fbca1256d5674b0143c77c18da92b495f0215ca38d2f601c23e'
    'cd93cf904a44185e2b9774eacfb72721d7807de621f44ce8206fbe21e8526a97'
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
