#!/usr/bin/env python
"""Signingscript task functions.

Attributes:
    FORMAT_TO_SIGNING_FUNCTION (frozendict): a mapping between signing format
        and signing function. If not specified, use the `default` signing
        function.

"""
import aiohttp
from frozendict import frozendict
import logging
import os
import random
import traceback

from datadog import statsd
import platform

from scriptworker.exceptions import ScriptWorkerException, TaskVerificationError
from scriptworker.utils import retry_request, get_single_item_from_sequence

from signingscript.sign import get_suitable_signing_servers, sign_gpg, \
    sign_jar, sign_macapp, sign_signcode, sign_widevine, sign_file
from signingscript.exceptions import SigningServerError

log = logging.getLogger(__name__)

FORMAT_TO_SIGNING_FUNCTION = frozendict({
    "gpg": sign_gpg,
    "jar": sign_jar,
    "macapp": sign_macapp,
    "osslsigncode": sign_signcode,
    "sha2signcode": sign_signcode,
    # sha2signcodestub uses a generic sign_file
    "signcode": sign_signcode,
    "widevine": sign_widevine,
    "widevine_blessed": sign_widevine,
    "default": sign_file,
})


# task_cert_type {{{1
def task_cert_type(context):
    """Extract task certificate type.

    Args:
        context (Context): the signing context.

    Raises:
        TaskVerificationError: if the number of cert scopes is not 1.

    Returns:
        str: the cert type.

    """
    prefix = _get_cert_prefix(context)
    scopes = context.task['scopes']
    return get_single_item_from_sequence(
        scopes,
        condition=lambda scope: scope.startswith(prefix),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No scope starting with "{}" found'.format(prefix),
        too_many_item_error_message='More than one scope starting with "{}"'.format(prefix),
    )


# task_signing_formats {{{1
def task_signing_formats(context):
    """Get the list of signing formats from the task signing scopes.

    Args:
        context (Context): the signing context.

    Returns:
        list: the signing formats.

    """
    prefix = _get_format_prefix(context)
    return [scope.split(':')[-1] for scope in context.task['scopes'] if scope.startswith(prefix)]


def _get_cert_prefix(context):
    return _get_scope_prefix(context, 'cert')


def _get_format_prefix(context):
    return _get_scope_prefix(context, 'format')


def _get_scope_prefix(context, sub_namespace):
    prefix = context.config['taskcluster_scope_prefix']
    prefix = prefix if prefix.endswith(':') else '{}:'.format(prefix)
    return '{}{}:'.format(prefix, sub_namespace)


# get_token {{{1
async def get_token(context, output_file, cert_type, signing_formats):
    """Retrieve a token from the signingserver tied to my ip.

    Args:
        context (Context): the signing context
        output_file (str): the path to write the token to.
        cert_type (str): the cert type used to find an appropriate signing server
        signing_formats (list): the signing formats used to find an appropriate
            signing server

    Raises:
        SigningServerError: on failure

    """
    token = None
    data = {
        "slave_ip": context.config['my_ip'],
        "duration": context.config["token_duration_seconds"],
    }
    signing_servers = get_suitable_signing_servers(
        context.signing_servers, cert_type,
        signing_formats
    )
    random.shuffle(signing_servers)
    for s in signing_servers:
        log.info("getting token from %s", s.server)
        url = "https://{}/token".format(s.server)
        auth = aiohttp.BasicAuth(s.user, password=s.password)
        try:
            token = await retry_request(context, url, method='post', data=data,
                                        auth=auth, return_type='text')
            if token:
                break
        except ScriptWorkerException:
            traceback.print_exc()
            continue
    else:
        raise SigningServerError("Cannot retrieve signing token")
    with open(output_file, "w") as fh:
        print(token, file=fh, end="")


# sign {{{1
async def sign(context, path, signing_formats):
    """Call the appropriate signing function per format, for a single file.

    Args:
        context (Context): the signing context
        path (str): the source file to sign
        signing_formats (list): the formats to sign with

    Returns:
        list: the list of paths generated. This will be a list of one, unless
            there are detached sigfiles.

    """
    output = path
    # Loop through the formats and sign one by one.
    for fmt in signing_formats:
        signing_func = FORMAT_TO_SIGNING_FUNCTION.get(
            fmt, FORMAT_TO_SIGNING_FUNCTION['default']
        )
        log.info("sign(): Signing {} with {}...".format(output, fmt))
        metric_tags = [
            'format:{}'.format(fmt),
            'host:{}'.format(platform.node()),
            'app:signingscript'
        ]
        with statsd.timed('signingfunc.time', tags=metric_tags):
            output = await signing_func(context, output, fmt)
    # We want to return a list
    if not isinstance(output, (tuple, list)):
        output = [output]
    return output


# _sort_formats {{{1
def _sort_formats(formats):
    """Order the signing formats.

    Certain formats need to happen before or after others, e.g. gpg after
    any format that modifies the binary.

    Args:
        formats (list): the formats to order.

    Returns:
        list: the ordered formats.

    """
    # Widevine formats must be after other formats other than macapp; GPG must
    # be last.
    for fmt in ("widevine", "widevine_blessed", "macapp", "gpg"):
        if fmt in formats:
            formats.remove(fmt)
            formats.append(fmt)
    return formats


# build_filelist_dict {{{1
def build_filelist_dict(context, all_signing_formats):
    """Build a dictionary of cot-downloaded paths and formats.

    Scriptworker will pre-download and pre-verify the `upstreamArtifacts`
    in our `work_dir`.  Let's build a dictionary of relative `path` to
    a dictionary of `full_path` and signing `formats`.

    Args:
        context (Context): the signing context
        all_signing_formats (list): the superset of valid signing formats,
            based on the task scopes.  If the file signing formats are not
            a subset, throw an exception.

    Raises:
        TaskVerificationError: if the files don't exist on disk, or the
            file signing formats are not a subset of all_signing_formats.

    Returns:
        dict of dicts: the dictionary of relative `path` to a dictionary with
            `full_path` and a list of signing `formats`.

    """
    filelist_dict = {}
    all_signing_formats_set = set(all_signing_formats)
    messages = []
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        for path in artifact_dict['paths']:
            full_path = os.path.join(
                context.config['work_dir'], 'cot', artifact_dict['taskId'],
                path
            )
            if not os.path.exists(full_path):
                messages.append("{} doesn't exist!".format(full_path))
            formats_set = set(artifact_dict['formats'])
            if not set(formats_set).issubset(all_signing_formats_set):
                messages.append("{} {} illegal format(s) {}!".format(
                    artifact_dict['taskId'], path,
                    formats_set.difference(all_signing_formats_set)
                ))
            filelist_dict[path] = {
                "full_path": full_path,
                "formats": _sort_formats(artifact_dict['formats']),
            }
    if messages:
        raise TaskVerificationError(messages)
    return filelist_dict
