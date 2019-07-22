#!/usr/bin/env python
"""Signingscript task functions.

Attributes:
    FORMAT_TO_SIGNING_FUNCTION (frozendict): a mapping between signing format
        and signing function. If not specified, use the `default` signing
        function.

"""
import aiohttp
import asyncio
from frozendict import frozendict
import logging
import os
import random
import re

from scriptworker.exceptions import ScriptWorkerException, TaskVerificationError
from scriptworker.utils import retry_request, get_single_item_from_sequence

from signingscript.sign import get_suitable_signing_servers, sign_gpg, \
    sign_jar, sign_macapp, sign_signcode, sign_widevine, sign_file, \
    sign_mar384_with_autograph_hash, sign_gpg_with_autograph, \
    sign_omnija
from signingscript.exceptions import SigningServerError
from signingscript.utils import is_autograph_signing_format

log = logging.getLogger(__name__)

FORMAT_TO_SIGNING_FUNCTION = frozendict({
    # TODO: Remove the next item (in favor of the regex one), once Focus is migrated
    "autograph_focus": sign_jar,
    "autograph_apk_.+": sign_jar,
    "autograph_hash_only_mar384(:\\w+)?": sign_mar384_with_autograph_hash,
    "autograph_stage_mar384(:\\w+)?": sign_mar384_with_autograph_hash,
    "gpg": sign_gpg,
    "autograph_gpg": sign_gpg_with_autograph,
    "jar": sign_jar,
    "focus-jar": sign_jar,
    "macapp": sign_macapp,
    "osslsigncode": sign_signcode,
    "sha2signcode": sign_signcode,
    # sha2signcodestub uses a generic sign_file
    "signcode": sign_signcode,
    "widevine": sign_widevine,
    "autograph_widevine": sign_widevine,
    "autograph_omnija": sign_omnija,
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
    prefixes = _get_cert_prefixes(context)
    scopes = _extract_scopes_from_unique_prefix(
        scopes=context.task['scopes'],
        prefixes=prefixes
    )
    return get_single_item_from_sequence(
        scopes,
        condition=lambda _: True,     # scopes must just contain 1 single item
        ErrorClass=TaskVerificationError,
        no_item_error_message='No scope starting with any of these prefixes {} found'.format(prefixes),
        too_many_item_error_message='More than one scope found',
    )


# task_signing_formats {{{1
def task_signing_formats(context):
    """Get the list of signing formats from the task payload.

    Args:
        context (Context): the signing context.

    Returns:
        set: the signing formats.

    """
    formats = set()
    for u in context.task.get('payload', {}).get('upstreamArtifacts', []):
        formats.update(u['formats'])
    return formats


def _extract_scopes_from_unique_prefix(scopes, prefixes):
    scopes = [
         scope
         for scope in scopes
         for prefix in prefixes
         if scope.startswith(prefix)
    ]
    _check_scopes_exist_and_all_have_the_same_prefix(scopes, prefixes)
    return scopes


def _get_cert_prefixes(context):
    return _get_scope_prefixes(context, 'cert')


def _get_scope_prefixes(context, sub_namespace):
    prefixes = context.config['taskcluster_scope_prefixes']
    prefixes = [
        prefix if prefix.endswith(':') else '{}:'.format(prefix)
        for prefix in prefixes
    ]
    return ['{}{}:'.format(prefix, sub_namespace) for prefix in prefixes]


def _check_scopes_exist_and_all_have_the_same_prefix(scopes, prefixes):
    for prefix in prefixes:
        if all(scope.startswith(prefix) for scope in scopes):
            break
    else:
        raise TaskVerificationError(
            'Scopes must exist and all have the same prefix. '
            'Given scopes: {}. Allowed prefixes: {}'.format(scopes, prefixes)
        )


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
        [fmt for fmt in signing_formats if not is_autograph_signing_format(fmt)]
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
        except (ScriptWorkerException, aiohttp.ClientError, asyncio.TimeoutError) as exc:
            log.warning("Error retrieving token: {}\nTrying the next server.".format(str(exc)))
            continue
    else:
        raise SigningServerError("Cannot retrieve signing token from any signing server.")
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
        signing_func = _get_signing_function_from_format(fmt)
        log.info("sign(): Signing {} with {}...".format(output, fmt))
        output = await signing_func(context, output, fmt)
    # We want to return a list
    if not isinstance(output, (tuple, list)):
        output = [output]
    return output


def _get_signing_function_from_format(format):
    try:
        _, signing_function = get_single_item_from_sequence(
            FORMAT_TO_SIGNING_FUNCTION.items(),
            condition=lambda item: re.match(item[0], format) is not None,
        )
        return signing_function
    except ValueError:
        # Regex may catch several candidate. If so, we fall back to the exact match.
        # If nothing matches, then we fall back to default
        return FORMAT_TO_SIGNING_FUNCTION.get(format, FORMAT_TO_SIGNING_FUNCTION['default'])


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
    for fmt in ("widevine", "autograph_widevine", "autograph_omnija",
                "macapp", "gpg", "autograph_gpg",
                ):
        if fmt in formats:
            formats.remove(fmt)
            formats.append(fmt)
    return formats


# build_filelist_dict {{{1
def build_filelist_dict(context):
    """Build a dictionary of cot-downloaded paths and formats.

    Scriptworker will pre-download and pre-verify the `upstreamArtifacts`
    in our `work_dir`.  Let's build a dictionary of relative `path` to
    a dictionary of `full_path` and signing `formats`.

    Args:
        context (Context): the signing context

    Raises:
        TaskVerificationError: if the files don't exist on disk

    Returns:
        dict of dicts: the dictionary of relative `path` to a dictionary with
            `full_path` and a list of signing `formats`.

    """
    filelist_dict = {}
    messages = []
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        for path in artifact_dict['paths']:
            full_path = os.path.join(
                context.config['work_dir'], 'cot', artifact_dict['taskId'],
                path
            )
            if not os.path.exists(full_path):
                messages.append("{} doesn't exist!".format(full_path))
            filelist_dict[path] = {
                "full_path": full_path,
                "formats": _sort_formats(artifact_dict['formats']),
            }
    if messages:
        raise TaskVerificationError(messages)
    return filelist_dict
