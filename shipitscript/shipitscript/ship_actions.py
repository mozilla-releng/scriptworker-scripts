import logging

from shipitscript.shipitapi import Release_V2
from shipitscript.utils import (
    check_release_has_values_v2,
    get_auth_primitives_v2,
    get_request_headers,
)

log = logging.getLogger(__name__)


def get_shipit_api_instance(shipit_config):
    (
        tc_client_id,
        tc_access_token,
        api_root,
        timeout_in_seconds,
    ) = get_auth_primitives_v2(shipit_config)

    release_api = Release_V2(
        taskcluster_client_id=tc_client_id,
        taskcluster_access_token=tc_access_token,
        api_root=api_root,
        timeout=timeout_in_seconds,
    )
    headers = get_request_headers(api_root)

    return release_api, headers


def get_shippable_revision(repo, last_shipped_revision):
    pass


def get_most_recent_shipped_revision(product, channel, shipit_config):
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info('Call Ship-it to retrieve all releases matching criteria ...')
    # TODO add proper parameters here
    all_releases = release_api.get_releases(headers=headers)
    # XXX: Ship-it API already sorts the releases based on their version so the
    # tail of the list is the most recent  version we have shipped based on
    # https://github.com/mozilla-releng/shipit/blob/master/api/src/shipit_api/api.py#L131
    most_recent_release = all_releases[-1]
    return most_recent_release['revision']


def get_next_release_version(product, channel, shipit_config):
    release_api, headers = get_shipit_api_instance(shipit_config)


def start_new_release(
    self,
    product,
    repo,
    channel,
    release_name,
    version,
    revision,
    phase,
    shipit_config,
    headers={},
):
    release_api, headers = get_shipit_api_instance(shipit_config)
    release_name = ""

    log.info('creating a new release...')
    release_api.create_new_release(
        product, channel, release_name, version, revision, headers=headers
    )
    release_api.trigger_release_phase(
        product, channel, release_name, phase, headers=headers
    )


def mark_as_shipped_v2(shipit_config, release_name):
    """Function to make a simple call to Ship-it API v2 to change a release
    status to 'shipped'
    """
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info('Marking the release as shipped...')
    release_api.update_status(release_name, status='shipped', headers=headers)
    check_release_has_values_v2(release_api, release_name, headers, status='shipped')
