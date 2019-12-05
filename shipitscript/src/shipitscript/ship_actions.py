import logging
import sys

from shipitscript import pushlog_scan
from shipitscript.shipitapi import Release_V2
from shipitscript.utils import check_release_has_values_v2, get_auth_primitives_v2, get_request_headers

log = logging.getLogger(__name__)


def get_shipit_api_instance(shipit_config):
    (tc_client_id, tc_access_token, api_root, timeout_in_seconds) = get_auth_primitives_v2(shipit_config)

    release_api = Release_V2(taskcluster_client_id=tc_client_id, taskcluster_access_token=tc_access_token, api_root=api_root, timeout=timeout_in_seconds)
    headers = get_request_headers(api_root)

    return release_api, headers


def get_shippable_revision(branch, last_shipped_revision, cron_revision):
    return pushlog_scan.get_shippable_revision_build(branch, last_shipped_revision, cron_revision)


def get_most_recent_shipped_revision(shipit_config, product, branch):
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info("Call Ship-it to retrieve all releases matching criteria")
    all_releases = release_api.get_releases(product, branch, status="shipped", headers=headers)
    # XXX: Ship-it API already sorts the releases based on their version so the
    # tail of the list is the most recent  version we have shipped based on
    # https://github.com/mozilla-releng/shipit/blob/master/api/src/shipit_api/api.py#L131
    try:
        most_recent_release = all_releases[-1]
        return most_recent_release["revision"]
    except IndexError:
        # return None should the list is empty
        log.error("The list of releases is empty")
        return
    except KeyError:
        log.error("No `revision` key present in the most recent release")
        return


def calculate_build_number(shipit_config, product, branch, version):
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info("Call Ship-it to retrieve all releases matching criteria ...")
    all_builds = release_api.get_releases(product, branch, status="shipped,aborted,scheduled", version=version, headers=headers)

    build_numbers = [r["build_number"] for r in all_builds]
    if not build_numbers:
        log.info("No other valid build numbers found, returning 1")
        return 1

    log.info("Choosing the max build_number in the findings and bumping it")
    return max(build_numbers) + 1


def releases_are_disabled(shipit_config, product, branch):
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info("Call Ship-it to check for disabled products across branches")
    disabled_products = release_api.get_disabled_products(headers=headers)

    return branch in disabled_products.get(product, [])


def start_new_release(shipit_config, product, branch, version, revision, phase):
    # safeguard to avoid creating releases if they have been disabled from UI
    if releases_are_disabled(shipit_config, product, branch):
        log.info("Releases are disabled. Silently exit ...")
        return

    # compute the build_number for the to-be-created release
    build_number = calculate_build_number(shipit_config, product, branch, version)
    if build_number != 1:
        log.info(f"Something is fishy in Ship-it, buildno returned is {build_number}.")
        sys.exit(1)

    release_api, headers = get_shipit_api_instance(shipit_config)
    log.info("creating a new release...")
    release_details = release_api.create_new_release(product, branch, version, build_number, revision, headers=headers)

    # grab the release name from the Ship-it create-release response
    release_name = release_details["name"]

    # minimize the possiblity of a  race condition in between creating the
    # release and triggering the specific `phase`. This is still possbile, but
    # we're calling this just before the API call to minimize the time-window
    if releases_are_disabled(shipit_config, product, branch):
        log.info("Releases are disabled. Silently exit ...")
        return
    release_api.trigger_release_phase(release_name, phase, headers=headers)


def mark_as_shipped_v2(shipit_config, release_name):
    """Function to make a simple call to Ship-it API v2 to change a release
    status to 'shipped'
    """
    release_api, headers = get_shipit_api_instance(shipit_config)

    log.info("Marking the release as shipped...")
    release_api.update_status(release_name, status="shipped", headers=headers)
    check_release_has_values_v2(release_api, release_name, headers, status="shipped")
