#!/usr/bin/env python
"""Signingscript task functions."""
import attr
import logging

from scriptworker_client.utils import get_artifact_path

log = logging.getLogger(__name__)


@attr.s
class App(object):
    orig_path = attr.ib(default='')
    app_path = attr.ib(default='')
    zip_path = attr.ib(default='')


def extract_and_sign(config, path, key):
    pass
    # extract
    # apple sign
    # return app_path


async def sign_and_notarize_all(config, task):
    """Sign and notarize all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    # work_dir = config['work_dir']
    # get entitlements -- default or from url

    # TODO get this from scopes?
    key = 'dep'

    # TODO unlock keychain

    # artifact_paths = [
    #     {'archive_path': '...', 'app_path': '...', 'zip_path': '...'}
    # ]
    all_paths = []
    for upstream_artifact_info in task['payload']['upstreamArtifacts']:
        for subpath in upstream_artifact_info['paths']:
            orig_path = get_artifact_path(
                upstream_artifact_info['taskId'], subpath, work_dir=config['work_dir'],
            )
            all_paths.append(App(orig_path=orig_path))

    for app in all_paths:
        # XXX we may be able to do this concurrently?
        app.app_path = extract_and_sign(config, app.orig_path, key)

    # if notarize:
        # notarize, concurrent across `notary_accounts`
        # poll
        # staple
    # copy to artifact_dir
