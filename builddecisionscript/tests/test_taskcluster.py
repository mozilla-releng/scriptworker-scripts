# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os

import pytest

from builddecisionscript.util.taskcluster import get_taskcluster_options


def test_get_taskcluster_options(tmp_path, monkeypatch):
    credentials = {"clientId": "test-client", "accessToken": "test-token"}
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps(credentials))

    fd = os.open(str(creds_file), os.O_RDWR)
    try:
        monkeypatch.setenv("TASKCLUSTER_CREDENTIALS_FD", str(fd))
        monkeypatch.setenv("TASKCLUSTER_ROOT_URL", "https://tc.example.com")

        result = get_taskcluster_options()

        assert result == {
            "rootUrl": "https://tc.example.com",
            "credentials": credentials,
        }
    finally:
        os.close(fd)
