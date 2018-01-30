import logging
import shipitapi

from datetime import datetime

log = logging.getLogger(__name__)


def mark_as_shipped(ship_it_instance_config, release_name):
    """Method to make a simple call to Ship-it API to change a release
    status to 'shipped'
    """
    auth = (ship_it_instance_config['username'], ship_it_instance_config['password'])
    api_root = ship_it_instance_config['api_root']
    timeout_in_seconds = int(ship_it_instance_config.get('timeout_in_seconds', 60))
    release_api = shipitapi.Release(auth, api_root=api_root, timeout=timeout_in_seconds)

    shipped_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    log.info('Marking the release as shipped with {} timestamp...'.format(shipped_at))
    release_api.update(release_name, status='shipped', shippedAt=shipped_at)
