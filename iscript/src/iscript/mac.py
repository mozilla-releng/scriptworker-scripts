#!/usr/bin/env python
"""Signingscript task functions."""
import asyncio
import attr
from glob import glob
import logging
import os

from scriptworker_client.utils import (
    extract_tarball,
    get_artifact_path,
    makedirs,
    raise_future_exceptions,
    rm,
)
from iscript.exceptions import IScriptError

log = logging.getLogger(__name__)


INITIAL_FILES_TO_SIGN = (
    "Contents/MacOS/XUL",
    "Contents/MacOS/pingsender",
    "Contents/MacOS/*.dylib",
    "Contents/MacOS/crashreporter.app/Contents/MacOS/minidump-analyzer",
    "Contents/MacOS/crashreporter.app/Contents/MacOS/crashreporter",
    "Contents/MacOS/firefox-bin",
    "Contents/MacOS/plugin-container.app/Contents/MacOS/plugin-container",
    "Contents/MacOS/updater.app/Contents/MacOS/org.mozilla.updater",
    "Contents/MacOS/firefox",
)


@attr.s
class App(object):
    orig_path = attr.ib(default='')
    parent_dir = attr.ib(default='')
    app_path = attr.ib(default='')
    zip_path = attr.ib(default='')


async def sign(config, app, key, entitlements_path):
    """Extract the .app from a tarfile and sign it.

    Args:
        config (dict): the running config
        from_ (str): the tarfile path
        parent_dir (str): the top level directory to extract the app into
        key (str): the nick of the key to use to sign with
    """
    key_config = get_key_config(config, key)
    app.app_path = get_app_dir(app.parent_dir)
    # xattr -cr app.app_path
    # codesign --force -o runtime --verbose --sign $IDENTITY
    #    --entitlements entitlements_path
    # find "$BUNDLE" -type f -exec \
    #    codesign --force -o runtime --verbose --sign "$IDENTITY" \
    #    --entitlements ${ENTITLEMENTS_FILE} {} \;
    # codesign --force -o runtime --verbose --sign "$IDENTITY" \
    #   --entitlements ${ENTITLEMENTS_FILE} "$BUNDLE"
    # codesign -vvv --deep --strict "$BUNDLE"

    # return app_path


def get_app_dir(parent_dir):
    """Get the .app directory in a ``parent_dir``.

    Args:
        parent_dir (str): the parent directory path

    Raises:
        UnknownAppDir: if there is no single app dir

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
    key_config = get_key_config(config, key)

    all_paths = []
    futures = []
    for upstream_artifact_info in task['payload']['upstreamArtifacts']:
        for subpath in upstream_artifact_info['paths']:
            orig_path = get_artifact_path(
                upstream_artifact_info['taskId'], subpath, work_dir=config['work_dir'],
            )
            all_paths.append(App(orig_path=orig_path))

    # extract
    for counter, app in all_paths:
        app.parent_dir = os.path.join(work_dir, str(counter))
        rm(app.parent_dir)
        makedirs(app.parent_dir)
        futures.append(asyncio.ensure_future(
            extract_tarball(app.orig_path, app.parent_dir)
        ))
    await raise_future_exceptions(futures)

    # sign
    # TODO unlock keychain using key_config['signing_keychain'] and key_config['keychain_password']
    futures = []
    for app in all_paths:
        futures.append(asyncio.ensure_future(
            sign(key_config, app, entitlements_path)
        ))
    await raise_future_exceptions(futures)

    if key_config['notarize_type'] == 'multi_account':
        futures = []
        for app in all_paths:
            # ditto -c -k --norsrc --keepParent "${BUNDLE}" ${OUTPUT_ZIP_FILE}
            pass
        await raise_future_exceptions(futures)

        for app in all_paths:
            # notarize, concurrent across `notary_accounts`
            pass

        for app in all_paths:
            pass
            # poll

        for app in all_paths:
            # staple
            pass
    # tar up the app_dir, into artifact_dir
