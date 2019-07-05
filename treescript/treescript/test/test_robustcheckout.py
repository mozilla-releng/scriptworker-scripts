"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import hashlib
import os

ROBUSTCHKOUT_SHA_512 = (
    '87239f91776d2c8b910daf156661ba4109b073bd7138edd6267b2843f9c9735d'
    '74d322ff8f52cdea86ba5bf67bf31a101e4d5a8d4b173143b0e1cfd538b2da98'
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
