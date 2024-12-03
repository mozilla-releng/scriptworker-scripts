#!/usr/bin/env python
"""Signing script."""

import json
import logging
import os
from dataclasses import asdict

import aiohttp
import scriptworker.client

from signingscript.exceptions import SigningScriptError
from signingscript.task import apple_notarize_stacked, build_filelist_dict, sign, task_cert_type, task_signing_formats
from signingscript.utils import copy_to_dir, load_apple_notarization_configs, load_autograph_configs

log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    """Sign all the things.

    Args:
        context (Context): the signing context.

    """
    work_dir = context.config["work_dir"]
    async with aiohttp.ClientSession() as session:
        all_signing_formats = task_signing_formats(context)
        if {"autograph_gpg", "gcp_prod_autograph_gpg", "stage_autograph_gpg"}.intersection(all_signing_formats):
            if not context.config.get("gpg_pubkey"):
                raise Exception("GPG format is enabled but gpg_pubkey is not defined")
            if not os.path.exists(context.config["gpg_pubkey"]):
                raise Exception("gpg_pubkey ({}) doesn't exist!".format(context.config["gpg_pubkey"]))

        if {"autograph_widevine", "gcp_prod_autograph_widevine", "stage_autograph_widevine"}.intersection(all_signing_formats):
            if not context.config.get("widevine_cert"):
                raise Exception("Widevine format is enabled, but widevine_cert is not defined")

        if {"apple_notarization", "apple_notarization_geckodriver", "apple_notarization_stacked"}.intersection(all_signing_formats):
            if not context.config.get("apple_notarization_configs", False):
                raise Exception("Apple notarization is enabled but apple_notarization_configs is not defined")
            setup_apple_notarization_credentials(context)

        context.session = session
        context.autograph_configs = load_autograph_configs(context.config["autograph_configs"])

        # TODO: Make task.sign take in the whole filelist_dict and return a dict of output files.
        #       That would likely mean changing all behaviors to accept and deal with multiple files at once.

        filelist_dict = build_filelist_dict(context)
        for path, path_dict in filelist_dict.items():
            if path_dict["formats"] == ["apple_notarization_stacked"]:
                # Skip if only format is notarization_stacked - handled below
                continue
            if "apple_notarization_stacked" in path_dict["formats"]:
                raise SigningScriptError("apple_notarization_stacked cannot be mixed with other signing types")
            copy_to_dir(path_dict["full_path"], context.config["work_dir"], target=path)
            log.info("signing %s", path)
            output_files = await sign(context, os.path.join(work_dir, path), path_dict["formats"], authenticode_comment=path_dict.get("comment"))
            for source in output_files:
                source = os.path.relpath(source, work_dir)
                copy_to_dir(os.path.join(work_dir, source), context.config["artifact_dir"], target=source)
            if {"autograph_gpg", "gcp_prod_autograph_gpg", "stage_autograph_gpg"}.intersection(set(path_dict["formats"])):
                copy_to_dir(context.config["gpg_pubkey"], context.config["artifact_dir"], target="public/build/KEY")

        # notarization_stacked is a special format that takes in all files at once instead of sequentially like other formats
        # Should be fixed in https://github.com/mozilla-releng/scriptworker-scripts/issues/980
        notarization_dict = {path: path_dict for path, path_dict in filelist_dict.items() if "apple_notarization_stacked" in path_dict["formats"]}
        if notarization_dict:
            output_files = await apple_notarize_stacked(context, notarization_dict)
            for source in output_files:
                source = os.path.relpath(source, work_dir)
                copy_to_dir(os.path.join(work_dir, source), context.config["artifact_dir"], target=source)

    log.info("Done!")


def get_default_config(base_dir=None):
    """Create the default config to work from.

    Args:
        base_dir (str, optional): the directory above the `work_dir` and `artifact_dir`.
            If None, use `..`  Defaults to None.

    Returns:
        dict: the default configuration dict.

    """
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "/src/signing/artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "signing_task_schema.json"),
        "verbose": True,
        "dmg": "dmg",
        "hfsplus": "hfsplus",
        "gpg_pubkey": None,
        "widevine_cert": None,
    }
    return default_config


def setup_apple_notarization_credentials(context):
    """Writes the notarization credential to a file

    Adds property to context: apple_credentials_path

    Args:
        context: Running task Context
    """
    cert_type = task_cert_type(context)
    apple_notarization_configs = load_apple_notarization_configs(context.config["apple_notarization_configs"])
    if cert_type not in apple_notarization_configs:
        raise SigningScriptError("Credentials not found for scope: %s" % cert_type)
    scope_credentials = apple_notarization_configs.get(cert_type)
    if len(scope_credentials) != 1:
        raise SigningScriptError("There should only be 1 scope credential, %s found." % len(scope_credentials))

    context.apple_credentials_path = os.path.join(
        os.path.dirname(context.config["apple_notarization_configs"]),
        "apple_api_key.json",
    )
    if os.path.exists(context.apple_credentials_path):
        # TODO: If we have different api keys for each product, this needs to overwrite every task:
        return
    # Convert dataclass to dict so json module can read it
    credential = asdict(scope_credentials[0])
    with open(context.apple_credentials_path, "wb") as credfile:
        credfile.write(json.dumps(credential).encode("ascii"))


def main():
    """Start signing script."""
    mohawk_log = logging.getLogger("mohawk")
    mohawk_log.setLevel(logging.INFO)
    return scriptworker.client.sync_main(async_main, default_config=get_default_config())


__name__ == "__main__" and main()
