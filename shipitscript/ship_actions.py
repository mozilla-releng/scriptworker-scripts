import logging
from datetime import datetime

import shipitapi

from shipitscript.utils import get_auth_primitives


log = logging.getLogger(__name__)


def mark_as_shipped(ship_it_instance_config, release_name):
    """Function to make a simple call to Ship-it API to change a release
    status to 'shipped'
    """
    auth, api_root, timeout_in_seconds = get_auth_primitives(ship_it_instance_config)
    release_api = shipitapi.Release(auth, api_root=api_root, timeout=timeout_in_seconds)
    shipped_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    log.info('Marking the release as shipped with {} timestamp...'.format(shipped_at))
    release_api.update(release_name, status='shipped', shippedAt=shipped_at)


def mark_as_started(ship_it_instance_config, release_name, data):
    """Function to make two consecutive calls to Ship-it v1; first simulates the
    RelMan `Do eeet` behavior by submitting the HTML response whilst the second one marks
    the release as started - similar to what Release Runner would do"""
    auth, api_root, timeout_in_seconds = get_auth_primitives(ship_it_instance_config)

    product = data['product']
    new_release = shipitapi.NewRelease(auth, api_root=api_root,
                                       timeout=timeout_in_seconds,
                                       csrf_token_prefix='{}-'.format(product))
    log.info('Submitting the release to Ship-it v1 ...')
    new_release.submit(**data)

    log.info('Marking the release as started ...')
    release_api = shipitapi.Release(auth, api_root=api_root,
                                    timeout=timeout_in_seconds)
    release_api.update(release_name, ready=1, complete=1, status="Started")
