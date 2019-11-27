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


def get_most_recent_shipped_revision(shipit_config, product, branch):
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info('Call Ship-it to retrieve all releases matching criteria ...')
    all_releases = release_api.get_releases(
            product, branch, status='shipped', headers=headers
    )
    # XXX: Ship-it API already sorts the releases based on their version so the
    # tail of the list is the most recent  version we have shipped based on
    # https://github.com/mozilla-releng/shipit/blob/master/api/src/shipit_api/api.py#L131
    try:
        most_recent_release = all_releases[-1]
        return most_recent_release['revision']
    except IndexError:
        # return None should the list is empty
        log.error('The list of releases is empty')
        return
    except KeyError:
        log.error('No `revision` key present in the most recent release')
        return


def calculate_build_number(shipit_config, product, branch, version):
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info('Call Ship-it to retrieve all releases matching criteria ...')
    all_releases = release_api.get_releases(
            product, branch, status='shipped,aborted,scheduled',
            version=version, headers=headers
    )

    build_numbers = [r['build_number'] for r in all_releases]
    last_build_number = max(build_numbers) or int(0)
    return last_build_number + 1


def releases_are_disabled(shipit_config, product, branch):
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info('Call Ship-it to check for disabled products across branches')
    disabled_products = release_api.get_disabled_products(headers=headers)

    if product in disabled_products:
        if branch in disabled_products[product]:
            log.info(f'Product {product} and {branch} are currently disabled')
            return True

    log.info(f'Product {product} and {branch} is enabled. Continuing ...')
    return False


def start_new_release(
        shipit_config, product,  branch, version, revision, phase
):
    # compute the build_number for the to-be-created release
    build_number = calculate_build_number(
        shipit_config, product, branch, version
    )

    # safeguard to avoid creating releases if they have been disabled from UI
    if releases_are_disabled(shipit_config, product, branch):
        return

    release_api, headers = get_shipit_api_instance(shipit_config)
    log.info('creating a new release...')
    release_details = release_api.create_new_release(
        product, branch, version, build_number, revision, headers=headers
    )

    # grab the release name from the Ship-it response
    release_name = release_details['name']

    # avoid race conditions in between creating the release and triggering the
    # specific `phase`
    if releases_are_disabled(shipit_config, product, branch):
        return
    release_api.trigger_release_phase(release_name, phase, headers=headers)


def mark_as_shipped_v2(shipit_config, release_name):
    """Function to make a simple call to Ship-it API v2 to change a release
    status to 'shipped'
    """
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info('Marking the release as shipped...')
    release_api.update_status(release_name, status='shipped', headers=headers)
    check_release_has_values_v2(release_api, release_name,
                                headers, status='shipped')
