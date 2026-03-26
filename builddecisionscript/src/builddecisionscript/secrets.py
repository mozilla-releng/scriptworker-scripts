# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging

import taskcluster

from .util.http import SESSION
from .util.taskcluster import get_taskcluster_options

logger = logging.getLogger(__name__)


def get_secret(secret_name, secret_key=None):
    secrets_client = taskcluster.Secrets(get_taskcluster_options(), session=SESSION)
    secret = secrets_client.get(secret_name)
    if secret_key:
        # This will raise a KeyError if the secret is populated but isn't in the
        # right form. Let's die so we see there's a problem and can fix it
        # sooner.
        return secret["secret"][secret_key]
    return secret
