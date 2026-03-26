# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging

from .util.http import SESSION

logger = logging.getLogger(__name__)


def get_secret(secret_name, secret_key=None):
    secret_url = f"http://taskcluster/secrets/v1/secret/{secret_name}"
    logging.info(f"Fetching secret at {secret_url} ...")
    res = SESSION.get(secret_url, timeout=60)
    res.raise_for_status()
    secret = res.json()
    if secret_key:
        return secret["secret"][secret_key]
    return secret
