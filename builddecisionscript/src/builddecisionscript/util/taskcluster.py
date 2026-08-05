# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import io
import json
import os


def get_taskcluster_options():
    """Return options for a Taskcluster client, reading credentials from the
    file written by scriptworker and updated on each reclaim."""
    creds_fd = int(os.environ["TASKCLUSTER_CREDENTIALS_FD"])
    try:
        with io.open(creds_fd, closefd=False) as f:
            credentials = json.load(f)
    finally:
        os.lseek(creds_fd, 0, os.SEEK_SET)
    return {
        "rootUrl": os.environ["TASKCLUSTER_ROOT_URL"],
        "credentials": credentials,
    }
