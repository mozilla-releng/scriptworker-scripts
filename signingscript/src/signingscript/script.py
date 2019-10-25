#!/usr/bin/env python
"""Signing script."""
import aiohttp
import logging
import os
import ssl

import scriptworker.client
from signingscript.task import (
    build_filelist_dict,
    sign,
    task_cert_type,
    task_signing_formats,
)
from signingscript.utils import (
    copy_to_dir,
)


log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    """Sign all the things.

    Args:
        context (Context): the signing context.

    """
    async with aiohttp.ClientSession() as session:
        all_signing_formats = task_signing_formats(context)
        if "gpg" in all_signing_formats or "autograph_gpg" in all_signing_formats:
            if not context.config.get("gpg_pubkey"):
                raise Exception("GPG format is enabled but gpg_pubkey is not defined")
            if not os.path.exists(context.config["gpg_pubkey"]):
                raise Exception(
                    "gpg_pubkey ({}) doesn't exist!".format(
                        context.config["gpg_pubkey"]
                    )
                )

        if "autograph_widevine" in all_signing_formats:
            if not context.config.get("widevine_cert"):
                raise Exception(
                    "Widevine format is enabled, but widevine_cert is not defined"
                )

        context.session = session
        work_dir = context.config["work_dir"]
        filelist_dict = build_filelist_dict(context)
        for path, path_dict in filelist_dict.items():
            copy_to_dir(path_dict["full_path"], context.config["work_dir"], target=path)
            log.info("signing %s", path)
            output_files = await sign(
                context, os.path.join(work_dir, path), path_dict["formats"]
            )
            for source in output_files:
                source = os.path.relpath(source, work_dir)
                copy_to_dir(
                    os.path.join(work_dir, source),
                    context.config["artifact_dir"],
                    target=source,
                )
            if "gpg" in path_dict["formats"] or "autograph_gpg" in path_dict["formats"]:
                copy_to_dir(
                    context.config["gpg_pubkey"],
                    context.config["artifact_dir"],
                    target="public/build/KEY",
                )
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
        "my_ip": "127.0.0.1",
        "schema_file": os.path.join(
            os.path.dirname(__file__), "data", "signing_task_schema.json"
        ),
        "verbose": True,
        "zipalign": "zipalign",
        "dmg": "dmg",
        "hfsplus": "hfsplus",
        "gpg_pubkey": None,
        "widevine_cert": None,
    }
    return default_config


def main():
    """Start signing script."""
    mohawk_log = logging.getLogger("mohawk")
    mohawk_log.setLevel(logging.INFO)
    return scriptworker.client.sync_main(
        async_main, default_config=get_default_config()
    )


__name__ == "__main__" and main()
