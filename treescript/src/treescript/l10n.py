#!/usr/bin/env python
"""Treescript l10n support.

Largely from https://hg.mozilla.org/mozilla-central/file/63ef0618ec9a07c438701e0357ef0d37abea0dd8/testing/mozharness/scripts/l10n_bumper.py

"""
import asyncio
import json
import logging
import os
import pprint
import tempfile
from copy import deepcopy

from scriptworker_client.aio import download_file, retry_async, semaphore_wrapper
from scriptworker_client.exceptions import DownloadError
from scriptworker_client.utils import load_json_or_yaml

from treescript.mercurial import run_hg_command
from treescript.task import CLOSED_TREE_MSG, DONTBUILD_MSG, get_dontbuild, get_ignore_closed_tree, get_l10n_bump_info, get_short_source_repo

log = logging.getLogger(__name__)


# build_locale_map {{{1
def build_locale_map(old_contents, new_contents):
    """Build a map of changed locales for the commit message.

    Args:
        old_contents (dict): the old l10n changesets
        new_contents (dict): the bumped l10n changesets

    Returns:
        dict: the changes per locale

    """
    locale_map = {}
    for key in old_contents:
        if key not in new_contents:
            locale_map[key] = "removed"
    for k, v in new_contents.items():
        if old_contents.get(k, {}).get("revision") != v["revision"]:
            locale_map[k] = v["revision"]
        elif old_contents.get(k, {}).get("platforms") != v["platforms"]:
            locale_map[k] = v["platforms"]
    return locale_map


# build_platform_dict {{{1
def build_platform_dict(bump_config, repo_path):
    """Build a dictionary of locale to list of platforms.

    Args:
        bump_config (dict): one of the dictionaries from the
            payload ``l10n_bump_info``
        repo_path (str): the path to the repo on disk

    Returns:
        dict: the platform dict

    """
    platform_dict = {}
    ignore_config = bump_config.get("ignore_config", {})
    for platform_config in bump_config["platform_configs"]:
        path = os.path.join(repo_path, platform_config["path"])
        log.info("Reading %s for %s locales...", path, platform_config["platforms"])
        with open(path, "r") as fh:
            contents = fh.read()
        for locale in contents.splitlines():
            # locale is 1st word in line in shipped-locales
            if platform_config.get("format") == "shipped-locales":
                locale = locale.split(" ")[0]
            if locale in ("en-US",):
                continue
            existing_platforms = set(platform_dict.get(locale, {}).get("platforms", []))
            platforms = set(platform_config["platforms"])
            ignore_platforms = set(ignore_config.get(locale, []))
            platforms = (platforms | existing_platforms) - ignore_platforms
            platform_dict[locale] = {"platforms": sorted(list(platforms))}
    log.info("Built platform_dict:\n%s" % pprint.pformat(platform_dict))
    return platform_dict


# get_latest_revision {{{1
async def get_latest_revision(locale, url):
    """Download the hg pushlog for the latest locale revision.

    Args:
        locale (str): the locale to query
        url (str): the [templatized] pushlog url

    Returns:
        tuple (locale, revision)

    """
    url = url % {"locale": locale}
    with tempfile.NamedTemporaryFile() as fp:
        path = fp.name
        await retry_async(download_file, args=(url, path), retry_exceptions=(DownloadError,))
        revision_info = load_json_or_yaml(path, is_path=True)
    last_push_id = revision_info["lastpushid"]
    revision = revision_info["pushes"][str(last_push_id)]["changesets"][0]
    log.info(f"locale {locale} revision {revision}")
    return (locale, revision)


# build_revision_dict {{{1
async def build_revision_dict(bump_config, repo_path, old_contents):
    """Add l10n revision information to the ``platform_dict``.

    If we have an ``l10n_repo_url``, use that as a template for the locale
    repo url. If ``pin`` is set in the ``old_contents`` for that locale, save
    the previous revision and pin. Otherwise, find the latest revision in the
    locale repo, and use that.

    The ``l10n_repo_url`` will look something like
    https://hg.mozilla.org/l10n-central/%(locale)s/json-pushes?version=2&tipsonly=1

    Otherwise, add a ``default`` revision to each locale in the
    ``platform_dict``.

    Args:
        bump_config (dict): one of the dictionaries from the
            payload ``l10n_bump_info``
        repo_path (str): the path to the repo on disk
        old_contents (dict): the old contents of the l10n changesets, if any.

    Returns:
        dict: locale to dictionary of platforms and revision

    """
    log.info("Building revision dict...")
    platform_dict = build_platform_dict(bump_config, repo_path)
    revision_dict = {}
    if bump_config.get("l10n_repo_url"):
        semaphore = asyncio.Semaphore(5)
        tasks = []
        for locale, value in platform_dict.items():
            if old_contents.get(locale, {}).get("pin"):
                value["revision"] = old_contents[locale]["revision"]
                value["pin"] = old_contents[locale]["pin"]
            else:
                tasks.append(asyncio.create_task(semaphore_wrapper(semaphore, get_latest_revision(locale, bump_config["l10n_repo_url"]))))
                value["pin"] = False
            revision_dict[locale] = value
        await asyncio.gather(*tasks)
        for task in tasks:
            (locale, revision) = task.result()
            revision_dict[locale]["revision"] = revision
    else:
        for k, v in platform_dict.items():
            v["revision"] = "default"
            revision_dict[k] = v
    log.info("revision_dict:\n%s" % pprint.pformat(revision_dict))
    return revision_dict


# build_commit_message {{{1
def build_commit_message(name, locale_map, dontbuild=False, ignore_closed_tree=False):
    """Build a commit message for the bumper.

    Args:
        name (str): the human readable name for the path (e.g. Firefox l10n
            changesets)
        locale_map (dict): l10n changeset changes, keyed by locale
        dontbuild (bool, optional): whether to add ``DONTBUILD`` to the
            comment. Defaults to ``False``
        ignore_closed_tree (bool, optional): whether to add ``CLOSED TREE``
            to the comment. Defaults to ``False``.

    Returns:
        str: the commit message

    """
    comments = ""
    approval_str = "r=release a=l10n-bump"
    for locale, revision in sorted(locale_map.items()):
        comments += "%s -> %s\n" % (locale, revision)
    if dontbuild:
        approval_str += DONTBUILD_MSG
    if ignore_closed_tree:
        approval_str += CLOSED_TREE_MSG
    message = "no bug - Bumping %s %s\n\n" % (name, approval_str)
    message += comments
    return message


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


# l10n_bump {{{1
async def l10n_bump(config, task, repo_path):
    """Perform a l10n revision bump.

    This function takes its inputs from task by using the ``get_l10n_bump_info``
    function from treescript.task. It then calculates the locales, the platforms
    for each locale, and the locale revision for each locale.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Raises:
        TaskVerificationError: if a file specified is not allowed, or
                               if the file is not in the target repository.

    Returns:
        int: non-zero if there are any changes.

    """
    log.info("Preparing to bump l10n changesets.")

    ignore_closed_tree = get_ignore_closed_tree(task)
    if not ignore_closed_tree:
        if not await check_treestatus(config, task):
            log.info("Treestatus is closed; skipping l10n bump.")
            return 0

    dontbuild = get_dontbuild(task)
    l10n_bump_info = get_l10n_bump_info(task)
    changes = 0

    for bump_config in l10n_bump_info:
        path = os.path.join(repo_path, bump_config["path"])
        old_contents = load_json_or_yaml(path, is_path=True)
        new_contents = await build_revision_dict(bump_config, repo_path, deepcopy(old_contents))
        if old_contents == new_contents:
            continue
        with open(path, "w") as fh:
            fh.write(json.dumps(new_contents, sort_keys=True, indent=4, separators=(",", ": ")))
        locale_map = build_locale_map(old_contents, new_contents)
        message = build_commit_message(bump_config["name"], locale_map, dontbuild=dontbuild, ignore_closed_tree=ignore_closed_tree)
        await run_hg_command(config, "commit", "-m", message, repo_path=repo_path)
        changes += 1
    return changes
