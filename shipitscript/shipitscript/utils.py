import logging
import urllib.parse

import arrow
from scriptworker.exceptions import ScriptWorkerTaskException

log = logging.getLogger(__name__)


def same_timing(time1, time2):
    """Function to decompress time from strings into datetime objects and
    compare them"""
    return arrow.get(time1) == arrow.get(time2)


def get_auth_primitives_v2(ship_it_instance_config):
    """Function to grab the primitives needed for shipitapi objects auth"""
    taskcluster_client_id = ship_it_instance_config['taskcluster_client_id']
    taskcluster_access_token = ship_it_instance_config['taskcluster_access_token']
    api_root = ship_it_instance_config['api_root_v2']
    timeout_in_seconds = int(ship_it_instance_config.get('timeout_in_seconds', 60))

    return (
        taskcluster_client_id,
        taskcluster_access_token,
        api_root,
        timeout_in_seconds,
    )


def get_request_headers(api_root):
    """Create headers needed for shipit requests"""
    # shipit API forces https:// by redirecting to the HTTPS port if the
    # request uses http:// or the traffic comes from the proxy, which sets the
    # "X-Forwarded-Proto" header to "https".
    # Shipitscript workers work in the same cluster with shipit, and they use
    # http:// and local addresses in order to bypass the load balancer.
    # The X-Forwarded-Proto header affects flask_talisman and prevents it from
    # upgrading the connection to https://.
    # The X-Forwarded-Port header explicitly specifies the used port to prevent
    # the API using the nginx proxy port to construct the mohawk payload.

    parsed_url = urllib.parse.urlsplit(api_root)
    if parsed_url.port:
        port = parsed_url.port
    else:
        if parsed_url.scheme == "https":
            port = 443
        else:
            port = 80
    headers = {"X-Forwarded-Proto": "https", "X-Forwarded-Port": str(port)}
    return headers


def check_release_has_values_v2(release_api, release_name, headers, **kwargs):
    """Function to make an API call to Ship-it v2 to grab release information
    and validate that fields that had just been updated are correctly reflected
    in the API returns"""
    release_info = release_api.getRelease(release_name, headers=headers)
    log.info("Full release details: {}".format(release_info))

    for key, value in kwargs.items():
        # special case for comparing times
        if not release_info.get(key) or release_info[key] != value:
            err_msg = "`{}`->`{}` don't exist or correspond.".format(key, value)
            raise ScriptWorkerTaskException(err_msg)

    log.info("All release fields have been correctly updated in Ship-it!")


def get_buildnum_from_version(next_version):
    pass
