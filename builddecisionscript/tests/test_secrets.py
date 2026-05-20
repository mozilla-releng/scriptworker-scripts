# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest.mock import MagicMock, patch

import builddecisionscript.secrets as secrets
import pytest


@pytest.mark.parametrize(
    "secret_name, secret, secret_key, expected",
    (
        ("secret1", {"secret": {"blah": "no peeking!!"}}, "blah", "no peeking!!"),
        (
            "secret2",
            {"secret": {"blah": "something"}},
            None,
            {"secret": {"blah": "something"}},
        ),
    ),
)
def test_get_secret(secret_name, secret, secret_key, expected):
    """Mock the secrets fetch, and test which values we get back."""
    fake_res = MagicMock()
    fake_res.json.return_value = secret
    fake_session = MagicMock()
    fake_session.get.return_value = fake_res

    with patch.object(secrets, "SESSION", new=fake_session):
        assert secrets.get_secret(secret_name, secret_key=secret_key) == expected
