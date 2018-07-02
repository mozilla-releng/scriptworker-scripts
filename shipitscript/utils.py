import arrow
import logging

from scriptworker.exceptions import ScriptWorkerTaskException


log = logging.getLogger(__name__)


def get_auth_primitives(ship_it_instance_config):
    """Function to grab the primitives needed for shipitapi objects auth"""
    auth = (ship_it_instance_config['username'], ship_it_instance_config['password'])
    api_root = ship_it_instance_config['api_root']
    timeout_in_seconds = int(ship_it_instance_config.get('timeout_in_seconds', 60))

    return (auth, api_root, timeout_in_seconds)


def check_release_has_values(release_api, release_name, **kwargs):
    """Function to make an API call to Ship-it v1 to grab release information
    and validate that fields that had just been updated are correctly reflected
    in the API returns"""
    # comprehensive dict with release details {'status': 'Started',
    # 'shippedAt': '...', 'branch': '...'}
    release_info = release_api.getRelease(release_name)
    log.info("Full release details: {}".format(release_info))

    for key, value in kwargs.items():
        # special case for comparing times
        if key == 'shippedAt':
            if not release_info.get(key) or not same_timing(release_info[key], value):
                err_msg = "`{}`->`{}` don't exist or correspond.".format(key, value)
                raise ScriptWorkerTaskException(err_msg)
        elif not release_info.get(key) or release_info[key] != value:
            err_msg = "`{}`->`{}` don't exist or correspond.".format(key, value)
            raise ScriptWorkerTaskException(err_msg)

    log.info("All release fields have been correctly updated in Ship-it!")


def same_timing(time1, time2):
    """Function to decompress time from strings into datetime objects and
    compare them"""
    return arrow.get(time1) == arrow.get(time2)
