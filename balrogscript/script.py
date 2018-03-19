#!/usr/bin/env python
"""Balrog script"""
from copy import deepcopy
import json
import logging
import os
import sys

from balrogscript.task import (
    get_manifest,
    get_task,
    get_task_action,
    get_task_server,
    get_upstream_artifacts,
    validate_task_schema,
)


log = logging.getLogger(__name__)


# create_locale_submitter {{{1
def create_locale_submitter(e, balrog_auth, config):
    from balrog.submitter.cli import NightlySubmitterV4, ReleaseSubmitterV9  # noqa: E402
    auth = balrog_auth

    if "tc_release" in e:
        log.info("Taskcluster Release style Balrog submission")

        complete_info = e['completeInfo']
        partial_info = e.get('partialInfo')
        submitter = ReleaseSubmitterV9(api_root=config['api_root'], auth=auth,
                                       dummy=config['dummy'])

        data = {
            'platform': e['platform'],
            'productName': e['appName'],
            'appVersion': e['appVersion'],
            'version': e['version'],
            'build_number': e['build_number'],
            'locale': e['locale'],
            'hashFunction': e['hashType'],
            'extVersion': e['extVersion'],
            'buildID': e['buildid'],
            'completeInfo': complete_info
        }
        if partial_info:
            data['partialInfo'] = partial_info
        return submitter, data

    elif "tc_nightly" in e:
        log.info("Taskcluster Nightly style Balrog submission")

        complete_info = e['completeInfo']
        partial_info = e.get('partialInfo')
        submitter = NightlySubmitterV4(api_root=config['api_root'], auth=auth,
                                       dummy=config['dummy'],
                                       url_replacements=e.get('url_replacements', []))

        data = {
            'platform': e["platform"],
            'buildID': e["buildid"],
            'productName': e["appName"],
            'branch': e["branch"],
            'appVersion': e["appVersion"],
            'locale': e["locale"],
            'hashFunction': e['hashType'],
            'extVersion': e["extVersion"],
            'completeInfo': complete_info
        }
        if partial_info:
            data['partialInfo'] = partial_info
        return submitter, data
    else:
        raise RuntimeError("Unknown Balrog submission style. Check manifest.json")


# submit_locale {{{1
def submit_locale(task, config, balrog_auth):
    """Submit a release blob to balrog."""
    from util.retry import retry  # noqa: E402
    upstream_artifacts = get_upstream_artifacts(task)

    # Read the manifest from disk
    manifest = get_manifest(config, upstream_artifacts)

    for e in manifest:
        # Get release metadata from manifest
        submitter, release = create_locale_submitter(e, balrog_auth, config)
        # Connect to balrog and submit the metadata
        retry(lambda: submitter.run(**release))


# schedule {{{1
def create_scheduler(**kwargs):
    from balrog.submitter.cli import ReleaseScheduler
    return ReleaseScheduler(**kwargs)


def schedule(task, config, balrog_auth):
    """Schedule a release to ship on balrog channel(s)"""
    from util.retry import retry  # noqa: E402
    auth = balrog_auth
    scheduler = create_scheduler(api_root=config['api_root'], auth=auth,
                                 dummy=config['dummy'])
    args = [
        task['payload']['product'].capitalize(),
        task['payload']['version'],
        task['payload']['build_number'],
        task['payload']['publish_rules'],
        task['payload']['release_eta'] or None,  # Send None if release_eta is ''
    ]
    # XXX optionally append background_rate if/when we want to support it

    # XXX should we catch requests.HTTPError and raise a scriptworker
    # error? maybe not since balrogscript isn't py3
    retry(lambda: scheduler.run(*args))


# submit_toplevel {{{1
def create_creator(**kwargs):
    from balrog.submitter.cli import ReleaseCreatorV9
    return ReleaseCreatorV9(**kwargs)


def create_pusher(**kwargs):
    from balrog.submitter.cli import ReleasePusher
    return ReleasePusher(**kwargs)


def submit_toplevel(task, config, balrog_auth):
    """Push a top-level release blob to balrog."""
    from util.retry import retry  # noqa: E402
    auth = balrog_auth
    partials = {}
    if task['payload'].get('partial_versions'):
        for v in task['payload']['partial_versions'].split(','):
            v = v.strip()  # we have whitespace after the comma
            version, build_number = v.split("build")
            partials[version] = {"buildNumber": build_number}

    creator = create_creator(
        api_root=config['api_root'], auth=auth,
        dummy=config['dummy'],
        # these are set for bz2, which we don't support.
        complete_mar_filename_pattern=None,
        complete_mar_bouncer_product_pattern=None,
    )
    pusher = create_pusher(
        api_root=config['api_root'], auth=auth,
        dummy=config['dummy'],
    )

    retry(lambda: creator.run(
        appVersion=task['payload']['app_version'],
        productName=task['payload']['product'].capitalize(),
        version=task['payload']['version'],
        buildNumber=task['payload']['build_number'],
        updateChannels=task['payload']['channel_names'],
        ftpServer=task['payload']['archive_domain'],
        bouncerServer=task['payload']['download_domain'],
        enUSPlatforms=task['payload']['platforms'],
        hashFunction='sha512',
        partialUpdates=partials,
        requiresMirrors=task['payload']['require_mirrors'],
    ))

    retry(lambda: pusher.run(
        productName=task['payload']['product'].capitalize(),
        version=task['payload']['version'],
        build_number=task['payload']['build_number'],
        rule_ids=task['payload']['rules_to_update'],
    ))


# usage {{{1
def usage():
    print >> sys.stderr, "Usage: {} CONFIG_FILE".format(sys.argv[0])
    sys.exit(2)


# setup_logging {{{1
def setup_logging(verbose=False):
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                        stream=sys.stdout,
                        level=log_level)


# update_config {{{1
def update_config(config, server='default'):
    config = deepcopy(config)

    config['api_root'] = config['server_config'][server]['api_root']
    username, password = (
        config['server_config'][server]['balrog_username'],
        config['server_config'][server]['balrog_password']
    )
    del(config['server_config'])
    return (username, password), config


# load_config {{{1
def load_config(path=None):
    try:
        with open(path) as fh:
            config = json.load(fh)
    except (ValueError, OSError, IOError) as e:
        print >> sys.stderr, "Can't read config file {}!\n{}".format(path, e)
        sys.exit(5)
    return config


# setup_config {{{1
def setup_config(config_path):
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]

    config = load_config(config_path)
    return config


# main {{{1
def main(config_path=None):
    config = setup_config(config_path)
    setup_logging(config['verbose'])

    task = get_task(config)
    action = get_task_action(task, config)
    validate_task_schema(config, task, action)

    server = get_task_server(task, config)
    balrog_auth, config = update_config(config, server)

    # hacking the tools repo dependency by first reading its location from
    # the config file and only then loading the module from subdfolder
    sys.path.insert(0, os.path.join(config['tools_location'], 'lib/python'))
    # Until we get rid of our tools dep, this import(s) will break flake8 E402

    if action == 'submit-toplevel':
        submit_toplevel(task, config, balrog_auth)
    elif action == 'schedule':
        schedule(task, config, balrog_auth)
    else:
        submit_locale(task, config, balrog_auth)


__name__ == '__main__' and main()
