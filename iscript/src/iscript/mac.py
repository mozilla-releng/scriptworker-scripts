#!/usr/bin/env python
"""Signingscript task functions."""
import attr
import logging

from scriptworker_client.utils import (
    get_artifact_path,
    makedirs,
    rm,
)
from iscript.exceptions import IScriptError
from iscript.utils import extract_tarfile

log = logging.getLogger(__name__)


@attr.s
class App(object):
    orig_path = attr.ib(default='')
    app_path = attr.ib(default='')
    zip_path = attr.ib(default='')


def extract_and_sign(config, from_, parent_dir, key, entitlements_path):
    """Extract the .app from a tarfile and sign it.

    Args:
        config (dict): the running config
        from_ (str): the tarfile path
        parent_dir (str): the top level directory to extract the app into
        key (str): the nick of the key to use to sign with
    """
    key_config = get_key_config(config, key)
    rm(parent_dir)
    makedirs(parent_dir)
    file_list = extract_tarfile(from_, parent_dir)
    app_dir = os.path.join(parent_dir, get_app_dir(file_list))
    # apple sign
    # return app_path


def get_app_dir(file_list):
    """
    """
    pass


def get_key_config(config, key, config_key='mac_config'):
    """Get the key subconfig from ``config``.

    Args:
        config (dict): the running config
        key (str): the key nickname, e.g. ``dep``
        config_key (str): the config key to use, e.g. ``mac_config``

    Raises:
        IScriptError: on invalid ``key`` or ``config_key``

    Returns:
        dict: the subconfig for the given ``config_key`` and ``key``

    """
    try:
        return config[config_key][key]
    except KeyError as e:
        raise IScriptError("Unknown key config {} {}: {}".format(config_key, key, e))


async def sign_and_notarize_all(config, task):
    """Sign and notarize all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    work_dir = config['work_dir']
    # TODO get entitlements -- default or from url
    entitlements_path = os.path.join(work_dir, "browser.entitlements.txt")

    # TODO get this from scopes?
    key = 'dep'

    all_paths = []
    for upstream_artifact_info in task['payload']['upstreamArtifacts']:
        for subpath in upstream_artifact_info['paths']:
            orig_path = get_artifact_path(
                upstream_artifact_info['taskId'], subpath, work_dir=config['work_dir'],
            )
            all_paths.append(App(orig_path=orig_path))

    # TODO unlock keychain
    for counter, app in all_paths:
        parent_dir = os.path.join(work_dir, str(counter))
        app.app_path = extract_and_sign(config, app.orig_path, parent_dir, key, entitlements_path)

    # if notarize:
        # notarize, concurrent across `notary_accounts`
        # poll
        # staple
    # copy to artifact_dir
