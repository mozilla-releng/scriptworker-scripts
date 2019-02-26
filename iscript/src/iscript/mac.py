#!/usr/bin/env python
"""Signingscript task functions."""
import asyncio
import logging
import os
import re

from scriptworker_client.utils import get_artifact_path

log = logging.getLogger(__name__)


def extract_and_sign(path, key):
    pass


async def sign_and_notarize_all(config, task):
    """Sign and notarize all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    # TODO get this from scopes?
    key = 'dep'

    # TODO unlock keychain

    for upstream_artifact_info in task['payload']['upstreamArtifacts']:
        for subpath in upstream_artifact_info['paths']:
            path = get_artifact_path(
                upstream_artifact_info['taskId'], subpath, work_dir=config['work_dir'],
            )
            # XXX We may be able to do this concurrently?
            extract_and_sign(config, path, key)
