#!/usr/bin/env python3
""" Github main script
"""
import logging
import os
import re

from scriptworker_client.client import sync_main

from githubscript.github import release
from githubscript.release_config import get_release_config
from githubscript.task import check_action_is_allowed, extract_common_scope_prefix, get_action, get_github_project

log = logging.getLogger(__name__)


async def async_main(config, task):
    prefix = extract_common_scope_prefix(config, task)
    project = get_github_project(task, prefix)
    # match the project on a regex
    project = {}
    # TODO: write a unittest for this
    for project in config["github_projects"].keys():
        project_re = re.compile(project)
        if project_re.match(project):
            project_config = config["github_projects"][project]

    if project == {}:
        raise NotImplementedError(f'project "{project}" doesn\'t match regex "{config["github_projects"].keys()}"')

    release_config = get_release_config(project_config, task["payload"], config)

    contact_github = bool(release_config.get("contact_github"))
    _warn_contact_github(contact_github)

    action = get_action(task, prefix)
    check_action_is_allowed(project_config, action)
    if action == "release":
        await release(release_config)
    else:
        raise NotImplementedError(f'Action "{action}" is not supported')

    log.info("Done!")


def _warn_contact_github(contact_github):
    if not contact_github:
        log.warning("This githubscript instance is not allowed to talk to Github.")


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    return {
        "work_dir": os.path.join(parent_dir, "work_dir"),
        "verbose": False,
    }


def main(config_path=None):
    sync_main(async_main, config_path=config_path, default_config=get_default_config(), should_verify_task=False)


__name__ == "__main__" and main()
