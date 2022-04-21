#!/usr/bin/env python3
""" Github main script
"""
import logging
import os

from scriptworker_client.client import sync_main
from scriptworker_client.exceptions import TaskError

from githubscript.geckoview import bump_geckoview
from githubscript.github import release
from githubscript.task import check_action_is_allowed, extract_common_scope_prefix, get_action, get_github_project
from githubscript.task_config import get_bump_config, get_release_config

log = logging.getLogger(__name__)


async def async_main(config, task):
    prefix = extract_common_scope_prefix(config, task)
    project = get_github_project(task, prefix)

    projects = config["github_projects"].keys()
    if project in projects:
        project_config = config["github_projects"][project]
    else:
        project_config = {}
        for p in projects:
            if not p.endswith("*"):
                continue
            cleaned = p.rstrip("*")
            if project.startswith(cleaned):
                if project_config != {}:
                    raise TaskError(f'project "{project}" matches multiple configs in "{projects}"')
                project_config = config["github_projects"][p]

    action = get_action(task, prefix)
    check_action_is_allowed(project_config, action)
    if action == "release":
        release_config = get_release_config(project_config, task["payload"], config)
        await release(release_config)
    elif action == "bump-geckoview":
        bump_config = get_bump_config(project_config, task["payload"], config)
        await bump_geckoview(bump_config)
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
