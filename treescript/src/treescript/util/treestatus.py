#!/usr/bin/env python
"""Treescript treestatus functions."""
import logging
import os

from scriptworker_client.aio import download_file, retry_async
from scriptworker_client.exceptions import DownloadError
from scriptworker_client.utils import load_json_or_yaml

from treescript.util.task import get_short_source_repo

log = logging.getLogger(__name__)


# check_treestatus {{{1
async def check_treestatus(config, task):
    """Return True if we can land based on treestatus.

    Args:
        config (dict): the running config
        task (dict): the running task

    Returns:
        bool: ``True`` if the tree is open.

    """
    tree = get_short_source_repo(task)
    url = "%s/trees/%s" % (config["treestatus_base_url"], tree)
    path = os.path.join(config["work_dir"], "treestatus.json")
    await retry_async(download_file, args=(url, path), retry_exceptions=(DownloadError,))

    treestatus = load_json_or_yaml(path, is_path=True)
    if treestatus["result"]["status"] != "closed":
        log.info("treestatus is %s - assuming we can land", repr(treestatus["result"]["status"]))
        return True
    return False
