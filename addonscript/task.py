"""Methods that deal with the task metadata to supply addonscript."""

import os
from scriptworker.exceptions import TaskVerificationError


def get_version():  # noqa
    raise Exception()


def get_channel():  # noqa
    raise Exception()


def build_filelist(context):
    """Build a list of cot-downloaded paths.

    Scriptworker will pre-download and pre-verify the `upstreamArtifacts`
    in our `work_dir`.  Let's build a list of relative of full paths.

    Args:
        context (SigningContext): the signing context

    Raises:
        TaskVerificationError: if the files don't exist on disk

    Returns:
        list: `full_path` of all files.

    """
    filelist = []
    messages = []
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        for path in artifact_dict['paths']:
            full_path = os.path.join(
                context.config['work_dir'], 'cot', artifact_dict['taskId'],
                path
            )
            if not os.path.exists(full_path):
                messages.append("{} doesn't exist!".format(full_path))
            filelist.append(full_path)
    if messages:
        raise TaskVerificationError(messages)
    return filelist
