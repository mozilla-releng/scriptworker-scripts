import logging

from shipitscript.shipitapi import Release_V2
from shipitscript.utils import (
    check_release_has_values_v2,
    get_auth_primitives_v2,
    get_request_headers,
)

log = logging.getLogger(__name__)


def are_releases_disabled(product, channel):
    pass


def get_most_recent_shipped_revision(product, channel):
    pass


def get_next_release_version(product, channel):
    pass


def get_shippable_revision(repo):
    pass


def get_buildnum_from_version(next_version):
    pass


def create_new_release(product, repo, next_version, shippable_revision):
    pass


def trigger_release_phase(release):
    pass


def mark_as_shipped_v2(ship_it_instance_config, release_name):
    """Function to make a simple call to Ship-it API v2 to change a release
    status to 'shipped'
    """
    (
        taskcluster_client_id,
        taskcluster_access_token,
        api_root,
        timeout_in_seconds,
    ) = get_auth_primitives_v2(ship_it_instance_config)
    release_api = Release_V2(
        taskcluster_client_id=taskcluster_client_id,
        taskcluster_access_token=taskcluster_access_token,
        api_root=api_root,
        timeout=timeout_in_seconds,
    )

    log.info('Marking the release as shipped...')
    headers = get_request_headers(api_root)
    release_api.update_status(release_name, status='shipped', headers=headers)
    check_release_has_values_v2(release_api, release_name, headers, status='shipped')
