#!/usr/bin/env python
"""Signingscript task functions."""
import asyncio
import logging
import os
import re
import subprocess

from scriptworker.utils import (
    retry_async,
    rm,
)

log = logging.getLogger(__name__)


async def sign_and_notarize_all(config, task):
    """Sign and notarize all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    for upstream_artifact_info in task['payload']['upstreamArtifacts']:
        for subpath in upstream_artifact_info['paths']:
            path = os.path.join(
                config['work_dir'], 'cot', upstream_artifact_info['taskId'],
                subpath
            )
