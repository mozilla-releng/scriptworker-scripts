# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging

from .util.http import SESSION

logger = logging.getLogger(__name__)


def get_secret(secret_name, secret_key=None):
    # XXX should we fall back to taskcluster api call if the proxy isn't running?
    #     (might be difficult and we may only hit that case if we run the docker
    #     image locally.)
    secret_url = f"http://taskcluster/secrets/v1/secret/{secret_name}"
    logging.info(f"Fetching secret at {secret_url} ...")
    res = SESSION.get(secret_url, timeout=60)
    # This will raise an error if the secret isn't populated or we have
    # infrastructure issues. Let's die so we see there's a problem.
    res.raise_for_status()
    secret = res.json()
    if secret_key:
        # This will raise a KeyError if the secret is populated but isn't in the
        # right form. Let's die so we see there's a problem and can fix it
        # sooner.
        return secret["secret"][secret_key]
    return secret
