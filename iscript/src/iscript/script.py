#!/usr/bin/env python
"""iScript: Apple signing and notarization."""
import aiohttp
import logging
import os

from scriptworker_client.client import sync_main


log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(config, task):
    """Sign all the things.

    Args:
        config (dict): the running config.
        task (dict): the running task.

    """
    # work_dir = config['work_dir']

    # get entitlements -- default or from url
    # extract
    # apple sign
    # notarize, concurrent across `notary_accounts`
    # poll
    # staple
    # copy to artifact_dir

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
        'work_dir': os.path.join(base_dir, 'work_dir'),
        'artifact_dir': os.path.join(base_dir, '/src/signing/artifact_dir'),
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'i_task_schema.json'),
        'notary_accounts': [],
    }
    return default_config


def main():
    """Start signing script."""
    return sync_main(async_main, default_config=get_default_config())


__name__ == '__main__' and main()
