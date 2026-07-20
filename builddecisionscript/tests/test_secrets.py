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
    fake_secrets_client = MagicMock()
    fake_secrets_client.get.return_value = secret

    with (
        patch("builddecisionscript.secrets.get_taskcluster_options", return_value={}),
        patch("builddecisionscript.secrets.taskcluster.Secrets", return_value=fake_secrets_client),
    ):
        assert secrets.get_secret(secret_name, secret_key=secret_key) == expected

    fake_secrets_client.get.assert_called_once_with(secret_name)
