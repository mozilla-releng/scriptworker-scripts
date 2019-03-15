#!/usr/bin/env python
"""iScript: Apple signing and notarization."""
import logging
import os

from scriptworker_client.client import sync_main
from iscript.mac import sign_and_notarize_all


log = logging.getLogger(__name__)


async def async_main(config, task):
    """Sign all the things.

    Args:
        config (dict): the running config.
        task (dict): the running task.

    """
    # XXX we can change behavior based on task definition. For now,
    # mac signing+notarizing is all we do.
    await sign_and_notarize_all(config, task)

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
        'work_dir': os.path.join(base_dir, 'work'),
        'artifact_dir': os.path.join(base_dir, 'artifacts'),
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'i_task_schema.json'),
        'local_notarization_accounts': [],
    }
    return default_config


def main():
    """Start signing script."""
    return sync_main(async_main, default_config=get_default_config())


__name__ == '__main__' and main()
