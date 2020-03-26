#!/usr/bin/env python
"""Balrog script"""
import json
import logging
import os
import sys

from immutabledict import immutabledict
from redo import retry  # noqa: E402

import scriptworker_client.client

from .submitter.cli import NightlySubmitterV4, ReleaseCreatorV9, ReleasePusher, ReleaseScheduler, ReleaseStateUpdater, ReleaseSubmitterV9
from .task import get_manifest, get_task_behavior, get_task_server, get_upstream_artifacts, validate_task_schema

log = logging.getLogger(__name__)


# create_locale_submitter {{{1
def create_locale_submitter(e, extra_suffix, auth0_secrets, config):
    if "tc_release" in e:
        log.info("Taskcluster Release style Balrog submission")

        submitter = ReleaseSubmitterV9(
            api_root=config["api_root"], auth0_secrets=auth0_secrets, dummy=config["dummy"], suffix=e.get("blob_suffix", "") + extra_suffix
        )

        data = {
            "platform": e["platform"],
            "productName": e["appName"],
            "appVersion": e["appVersion"],
            "version": e["version"],
            "build_number": e["build_number"],
            "locale": e["locale"],
            "hashFunction": e["hashType"],
            "extVersion": e["extVersion"],
            "buildID": e["buildid"],
            "completeInfo": e["completeInfo"],
        }
        if "partialInfo" in e:
            data["partialInfo"] = e["partialInfo"]
        return submitter, data

    elif "tc_nightly" in e:
        log.info("Taskcluster Nightly style Balrog submission")

        submitter = NightlySubmitterV4(
            api_root=config["api_root"], auth0_secrets=auth0_secrets, dummy=config["dummy"], url_replacements=e.get("url_replacements", [])
        )

        data = {
            "platform": e["platform"],
            "buildID": e["buildid"],
            "productName": e["appName"],
            "branch": e["branch"],
            "appVersion": e["appVersion"],
            "locale": e["locale"],
            "hashFunction": e["hashType"],
            "extVersion": e["extVersion"],
            "completeInfo": e["completeInfo"],
        }
        if "partialInfo" in e:
            data["partialInfo"] = e["partialInfo"]
        return submitter, data
    else:
        raise RuntimeError("Unknown Balrog submission style. Check manifest.json")


# submit_locale {{{1
def submit_locale(task, config, auth0_secrets):
    """Submit a release blob to balrog."""
    upstream_artifacts = get_upstream_artifacts(task)

    # Read the manifest from disk
    manifest = get_manifest(config, upstream_artifacts)

    suffixes = task["payload"].get("suffixes", [""])

    for e in manifest:
        for suffix in suffixes:
            # Get release metadata from manifest
            submitter, release = create_locale_submitter(e, suffix, auth0_secrets, config)
            # Connect to balrog and submit the metadata
            # Going back to the original number of attempts so that we avoid sleeping too much in between
            # retries to get Out-of-memory in the GCP workers. Until we figure out what's bumping the spike
            # in memory usage from 130 -> ~400 Mb, let's keep this as it was, historically
            retry(lambda: submitter.run(**release), jitter=5, sleeptime=10, max_sleeptime=30, attempts=10)


# schedule {{{1
def create_scheduler(**kwargs):
    return ReleaseScheduler(**kwargs)


def schedule(task, config, auth0_secrets):
    """Schedule a release to ship on balrog channel(s)"""
    scheduler = create_scheduler(api_root=config["api_root"], auth0_secrets=auth0_secrets, dummy=config["dummy"], suffix=task["payload"].get("blob_suffix", ""))
    args = [
        task["payload"]["product"].capitalize(),
        task["payload"]["version"],
        task["payload"]["build_number"],
        task["payload"]["publish_rules"],
        task["payload"].get("force_fallback_mapping_update", False),
        task["payload"]["release_eta"] or None,  # Send None if release_eta is ''
        task["payload"].get("background_rate"),
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


def submit_toplevel(task, config, auth0_secrets):
    """Push a top-level release blob to balrog."""
    partials = {}
    if task["payload"].get("partial_versions"):
        for v in task["payload"]["partial_versions"].split(","):
            v = v.strip()  # we have whitespace after the comma
            version, build_number = v.split("build")
            partials[version] = {"buildNumber": build_number}

    suffixes = list(task["payload"].get("update_line", {}).keys()) or [""]

    for suffix in suffixes:
        creator = create_creator(
            api_root=config["api_root"],
            auth0_secrets=auth0_secrets,
            dummy=config["dummy"],
            suffix=task["payload"].get("blob_suffix", "") + suffix,
            complete_mar_filename_pattern=task["payload"].get("complete_mar_filename_pattern"),
            complete_mar_bouncer_product_pattern=task["payload"].get("complete_mar_bouncer_product_pattern"),
        )

        retry(
            lambda: creator.run(
                appVersion=task["payload"]["app_version"],
                productName=task["payload"]["product"].capitalize(),
                version=task["payload"]["version"],
                buildNumber=task["payload"]["build_number"],
                updateChannels=task["payload"]["channel_names"],
                ftpServer=task["payload"]["archive_domain"],
                bouncerServer=task["payload"]["download_domain"],
                enUSPlatforms=task["payload"]["platforms"],
                hashFunction="sha512",
                partialUpdates=partials,
                requiresMirrors=task["payload"]["require_mirrors"],
                updateLine=task["payload"].get("update_line", {}).get(suffix),
            )
        )

    pusher = create_pusher(api_root=config["api_root"], auth0_secrets=auth0_secrets, dummy=config["dummy"], suffix=task["payload"].get("blob_suffix", ""))
    retry(
        lambda: pusher.run(
            productName=task["payload"]["product"].capitalize(),
            version=task["payload"]["version"],
            build_number=task["payload"]["build_number"],
            rule_ids=task["payload"]["rules_to_update"],
        )
    )


# set_readonly {{{1
def create_state_updater(**kwargs):
    return ReleaseStateUpdater(**kwargs)


def set_readonly(task, config, auth0_secrets):
    state_updater = create_state_updater(api_root=config["api_root"], auth0_secrets=auth0_secrets)
    args = [task["payload"]["product"].capitalize(), task["payload"]["version"], task["payload"]["build_number"]]
    retry(lambda: state_updater.run(*args))


# update_config {{{1
def update_config(config, server="default"):
    config = dict(config)

    config["api_root"] = config["server_config"][server]["api_root"]
    auth0_secrets = dict(
        domain=config["server_config"][server]["auth0_domain"],
        client_id=config["server_config"][server]["auth0_client_id"],
        client_secret=config["server_config"][server]["auth0_client_secret"],
        audience=config["server_config"][server]["auth0_audience"],
    )
    del config["server_config"]
    return auth0_secrets, immutabledict(config)


# load_config {{{1
def load_config(path=None):
    try:
        with open(path) as fh:
            config = json.load(fh)
    except (ValueError, OSError, IOError):
        log.fatal("Can't read config file %s", path)
        sys.exit(5)
    return config


# get_default_config {{{1
def get_default_config():
    """Create the default config to work from.

    Args:
        base_dir (str, optional): the directory above the `work_dir` and `artifact_dir`.
            If None, use `..`  Defaults to None.

    Returns:
        dict: the default configuration dict.

    """
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    default_config = {
        "schema_files": {
            "submit-locale": os.path.join(data_dir, "balrog_submit-locale_schema.json"),
            "submit-toplevel": os.path.join(data_dir, "balrog_submit-toplevel_schema.json"),
            "schedule": os.path.join(data_dir, "balrog_schedule_schema.json"),
            "set-readonly": os.path.join(data_dir, "balrog_set-readonly_schema.json"),
        }
    }
    return default_config


# main {{{1
async def async_main(config, task):
    action = get_task_behavior(task, config)
    validate_task_schema(config, task, action)

    server = get_task_server(task, config)
    auth0_secrets, config = update_config(config, server)

    if action == "submit-toplevel":
        submit_toplevel(task, config, auth0_secrets)
    elif action == "schedule":
        schedule(task, config, auth0_secrets)
    elif action == "set-readonly":
        set_readonly(task, config, auth0_secrets)
    else:
        submit_locale(task, config, auth0_secrets)


def main():
    return scriptworker_client.client.sync_main(async_main, default_config=get_default_config(), should_verify_task=False)


__name__ == "__main__" and main()
