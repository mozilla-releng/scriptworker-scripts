import logging

from shipitscript.shipitapi import Release_V2
from shipitscript.utils import (
    check_release_has_values_v2,
    get_auth_primitives_v2,
    get_request_headers,
)

log = logging.getLogger(__name__)


def get_shipit_api_instance(ship_it_instance_config):
    (
        taskcluster_client_id,
        taskcluster_access_token,
        api_root,
        timeout_in_seconds,
    ) = get_auth_primitives_v2(ship_it_instance_config)

    return Release_V2(
        taskcluster_client_id=taskcluster_client_id,
        taskcluster_access_token=taskcluster_access_token,
        api_root=api_root,
        timeout=timeout_in_seconds,
    )


def get_shippable_revision(repo, last_shipped_revision):
    pass


def get_most_recent_shipped_revision(product, channel):
    release_api = get_shipit_api_instance(ship_it_instance_config)
    headers = get_request_headers(api_root)


def get_next_release_version(product, channel):
    release_api = get_shipit_api_instance(ship_it_instance_config)
    headers = get_request_headers(api_root)


def start_new_release(self, product, repo, channel, release_name, version, revision, ship_it_instance_config, headers={}):
    release_api = get_shipit_api_instance(ship_it_instance_config)
    release_name = ""

    log.info('creating a new release...')
    headers = get_request_headers(api_root)
    release_api.create_new_release(product, channel, release_name, version, revision, headers=headers)
    release_api.trigger_release_phase(product, channel, release_name, headers=headers)


def mark_as_shipped_v2(ship_it_instance_config, release_name):
    """Function to make a simple call to Ship-it API v2 to change a release
    status to 'shipped'
    """
    release_api = get_shipit_api_instance(ship_it_instance_config)

    log.info('Marking the release as shipped...')
    headers = get_request_headers(api_root)
    release_api.update_status(release_name, status='shipped', headers=headers)
    check_release_has_values_v2(release_api, release_name, headers, status='shipped')
