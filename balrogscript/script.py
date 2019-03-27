#!/usr/bin/env python
"""Balrog script"""
from copy import deepcopy
import json
import logging
import os
import sys

from redo import retry  # noqa: E402

from balrogscript.task import (
    get_manifest,
    get_task,
    get_task_action,
    get_task_server,
    get_upstream_artifacts,
    validate_task_schema,
)
from .submitter.cli import (
    NightlySubmitterV4, ReleaseSubmitterV9,
    ReleaseScheduler,
    ReleaseCreatorV9,
    ReleasePusher,
)


log = logging.getLogger(__name__)


# create_locale_submitter {{{1
def create_locale_submitter(e, extra_suffix, balrog_auth, auth0_secrets, config):
    auth = balrog_auth

    if "tc_release" in e:
        log.info("Taskcluster Release style Balrog submission")

        submitter = ReleaseSubmitterV9(
            api_root=config['api_root'], auth=auth, auth0_secrets=auth0_secrets,
            dummy=config['dummy'],
            suffix=e.get('blob_suffix', '') + extra_suffix,
        )

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
            'completeInfo': e['completeInfo'],
        }
        if 'partialInfo' in e:
            data['partialInfo'] = e['partialInfo']
        return submitter, data

    elif "tc_nightly" in e:
        log.info("Taskcluster Nightly style Balrog submission")

        submitter = NightlySubmitterV4(api_root=config['api_root'], auth=auth,
                                       auth0_secrets=auth0_secrets,
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
            'completeInfo': e['completeInfo'],
        }
        if 'partialInfo' in e:
            data['partialInfo'] = e['partialInfo']
        return submitter, data
    else:
        raise RuntimeError("Unknown Balrog submission style. Check manifest.json")


# submit_locale {{{1
def submit_locale(task, config, balrog_auth, auth0_secrets):
    """Submit a release blob to balrog."""
    upstream_artifacts = get_upstream_artifacts(task)

    # Read the manifest from disk
    manifest = get_manifest(config, upstream_artifacts)

    suffixes = task['payload'].get('suffixes', [''])

    for e in manifest:
        for suffix in suffixes:
            # Get release metadata from manifest
            submitter, release = create_locale_submitter(e, suffix, balrog_auth, auth0_secrets, config)
            # Connect to balrog and submit the metadata
            retry(lambda: submitter.run(**release))


# schedule {{{1
def create_scheduler(**kwargs):
    return ReleaseScheduler(**kwargs)


def schedule(task, config, balrog_auth, auth0_secrets):
    """Schedule a release to ship on balrog channel(s)"""
    auth = balrog_auth
    scheduler = create_scheduler(
        api_root=config['api_root'], auth=auth,
        auth0_secrets=auth0_secrets,
        dummy=config['dummy'],
        suffix=task['payload'].get('blob_suffix', ''),
    )
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
    return ReleaseCreatorV9(**kwargs)


def create_pusher(**kwargs):
    return ReleasePusher(**kwargs)


def submit_toplevel(task, config, balrog_auth, auth0_secrets):
    """Push a top-level release blob to balrog."""
    auth = balrog_auth
    partials = {}
    if task['payload'].get('partial_versions'):
        for v in task['payload']['partial_versions'].split(','):
            v = v.strip()  # we have whitespace after the comma
            version, build_number = v.split("build")
            partials[version] = {"buildNumber": build_number}

    suffixes = task['payload'].get('update_line', {}).keys() or ['']

    for suffix in suffixes:
        creator = create_creator(
            api_root=config['api_root'], auth=auth,
            auth0_secrets=auth0_secrets,
            dummy=config['dummy'],
            suffix=task['payload'].get('blob_suffix', '') + suffix,
            complete_mar_filename_pattern=task['payload'].get('complete_mar_filename_pattern'),
            complete_mar_bouncer_product_pattern=task['payload'].get('complete_mar_bouncer_product_pattern'),
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
            updateLine=task['payload'].get('update_line', {}).get(suffix),
        ))

    pusher = create_pusher(
        api_root=config['api_root'], auth=auth,
        auth0_secrets=auth0_secrets,
        dummy=config['dummy'],
        suffix=task['payload'].get('blob_suffix', ''),
    )
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
    basic_auth = (
        config['server_config'][server]['balrog_username'],
        config['server_config'][server]['balrog_password'],
    )
    auth0_secrets = dict(
        domain=config['server_config'][server]['auth0_domain'],
        client_id=config['server_config'][server]['auth0_client_id'],
        client_secret=config['server_config'][server]['auth0_client_secret'],
        audience=config['server_config'][server]['auth0_audience'],
    )
    del(config['server_config'])
    return (basic_auth, auth0_secrets), config


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

    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    config = {
        'schema_files': {
            'submit-locale': os.path.join(data_dir, 'balrog_submit-locale_schema.json'),
            'submit-toplevel': os.path.join(data_dir, 'balrog_submit-toplevel_schema.json'),
            'schedule': os.path.join(data_dir, 'balrog_schedule_schema.json')
        },
    }
    config.update(load_config(config_path))
    return config


# main {{{1
def main(config_path=None):
    # TODO use scriptworker's sync_main(...)
    config = setup_config(config_path)
    setup_logging(config['verbose'])

    task = get_task(config)
    action = get_task_action(task, config)
    validate_task_schema(config, task, action)

    server = get_task_server(task, config)
    (balrog_auth, auth0_secrets), config = update_config(config, server)

    if action == 'submit-toplevel':
        submit_toplevel(task, config, balrog_auth, auth0_secrets)
    elif action == 'schedule':
        schedule(task, config, balrog_auth, auth0_secrets)
    else:
        submit_locale(task, config, balrog_auth, auth0_secrets)


__name__ == '__main__' and main()
