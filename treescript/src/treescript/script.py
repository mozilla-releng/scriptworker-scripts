#!/usr/bin/env python
"""Tree manipulation script."""

import logging
import os

from scriptworker_client.client import sync_main
from scriptworker_client.github import is_github_url

from treescript import github
from treescript.exceptions import TaskVerificationError
from treescript.util.task import get_source_repo

log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(config, task):
    """Run all the github things.

    Args:
        config (dict): the running config.
        task (dict): the running task.

    """
    source_repo = get_source_repo(task)
    if not is_github_url(source_repo):
        raise TaskVerificationError(f"Unsupported source repo {source_repo}, only github is supported")
    await github.do_actions(config, task)
    log.info("Done!")


# config {{{1
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
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "treescript_task_schema.json"),
    }
    return default_config


def main():
    """Start treescript."""
    return sync_main(async_main, default_config=get_default_config())


if __name__ == "__main__":
    main()
