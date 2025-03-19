#!/usr/bin/env python
"""Signingscript task functions.

Attributes:
    FORMAT_TO_SIGNING_FUNCTION (immutabledict): a mapping between signing format
        and signing function. If not specified, use the `default` signing
        function.

"""

import logging
import os

from immutabledict import immutabledict
from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

from signingscript.sign import (
    apple_notarize,
    apple_notarize_geckodriver,
    apple_notarize_openh264_plugin,
    apple_notarize_stacked,  # noqa: F401
    sign_authenticode,
    sign_file,
    sign_file_detached,
    sign_gpg_with_autograph,
    sign_macapp,
    sign_mar384_with_autograph_hash,
    sign_omnija,
    sign_widevine,
    sign_xpi,
)
from signingscript.utils import split_autograph_format

log = logging.getLogger(__name__)


FORMAT_TO_SIGNING_FUNCTION = immutabledict(
    {
        "autograph_hash_only_mar384": sign_mar384_with_autograph_hash,
        "autograph_stage_mar384": sign_mar384_with_autograph_hash,
        "autograph_gpg": sign_gpg_with_autograph,
        "autograph_widevine": sign_widevine,
        "autograph_omnija": sign_omnija,
        "autograph_langpack": sign_xpi,
        "autograph_authenticode_sha2": sign_authenticode,
        "autograph_authenticode_sha2_stub": sign_authenticode,
        "autograph_authenticode_sha2_rfc3161_stub": sign_authenticode,
        "autograph_authenticode_202404": sign_authenticode,
        "autograph_authenticode_202404_stub": sign_authenticode,
        "autograph_authenticode_ev": sign_authenticode,
        "autograph_authenticode_202412": sign_authenticode,
        "autograph_authenticode_202412_stub": sign_authenticode,
        "autograph_authenticode_ev_202412": sign_authenticode,
        "privileged_webextension": sign_xpi,
        "system_addon": sign_xpi,
        "autograph_rsa": sign_file_detached,
        "widevine": sign_widevine,
        "apple_notarization": apple_notarize,
        "apple_notarization_geckodriver": apple_notarize_geckodriver,
        "apple_notarization_openh264_plugin": apple_notarize_openh264_plugin,
        "macapp": sign_macapp,
        # This format is handled in script.py
        # Should be refactored in https://github.com/mozilla-releng/scriptworker-scripts/issues/980
        # "apple_notarization_stacked": apple_notarize_stacked,
        "default": sign_file,
    }
)


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
    if not context.task or not context.task["scopes"]:
        raise TaskVerificationError("No scopes found")

    prefixes = _get_cert_prefixes(context)
    scopes = _extract_scopes_from_unique_prefix(scopes=context.task["scopes"], prefixes=prefixes)
    return get_single_item_from_sequence(
        scopes,
        condition=lambda _: True,  # scopes must just contain 1 single item
        ErrorClass=TaskVerificationError,
        no_item_error_message="No scope starting with any of these prefixes {} found".format(prefixes),
        too_many_item_error_message="More than one scope found",
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
    for u in context.task.get("payload", {}).get("upstreamArtifacts", []):
        formats.update(u["formats"])
    return formats


def _extract_scopes_from_unique_prefix(scopes, prefixes):
    scopes = [scope for scope in scopes for prefix in prefixes if scope.startswith(prefix)]
    _check_scopes_exist_and_all_have_the_same_prefix(scopes, prefixes)
    return scopes


def _get_cert_prefixes(context):
    return _get_scope_prefixes(context, "cert")


def _get_scope_prefixes(context, sub_namespace):
    prefixes = context.config["taskcluster_scope_prefixes"]
    prefixes = [prefix if prefix.endswith(":") else "{}:".format(prefix) for prefix in prefixes]
    return ["{}{}:".format(prefix, sub_namespace) for prefix in prefixes]


def _check_scopes_exist_and_all_have_the_same_prefix(scopes, prefixes):
    for prefix in prefixes:
        if all(scope.startswith(prefix) for scope in scopes):
            break
    else:
        raise TaskVerificationError("Scopes must exist and all have the same prefix. Given scopes: {}. Allowed prefixes: {}".format(scopes, prefixes))


# sign {{{1
async def sign(context, path, signing_formats, **kwargs):
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
        try:
            size = os.path.getsize(output)
        except OSError:
            size = "??"
        log.info("sign(): Signing %s bytes in %s with %s...", size, output, fmt)
        output = await signing_func(context, output, fmt, **kwargs)
    # We want to return a list
    if not isinstance(output, (tuple, list)):
        output = [output]
    return output


def _get_signing_function_from_format(fmt_and_key_id):
    fmt, _ = split_autograph_format(fmt_and_key_id)

    if fmt.startswith(("autograph_xpi", "gcp_prod_autograph_xpi", "stage_autograph_xpi")):
        return sign_xpi
    if fn := FORMAT_TO_SIGNING_FUNCTION.get(fmt):
        return fn
    if fn := FORMAT_TO_SIGNING_FUNCTION.get(fmt.removeprefix("stage_").removeprefix("gcp_prod_")):
        return fn

    return FORMAT_TO_SIGNING_FUNCTION["default"]


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
    for fmt in (
        "widevine",
        "autograph_widevine",
        "gcp_prod_autograph_widevine",
        "stage_autograph_widevine",
        "autograph_omnija",
        "gcp_prod_autograph_omnija",
        "stage_autograph_omnija",
        "macapp",
        "autograph_rsa",
        "gcp_prod_autograph_rsa",
        "stage_autograph_rsa",
        "autograph_gpg",
        "gcp_prod_autograph_gpg",
        "stage_autograph_gpg",
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
        TaskVerificationError: if the files don't exist on disk or
                               if authenticode_comment is used without authenticode or on a non .msi

    Returns:
        dict of dicts: the dictionary of relative `path` to a dictionary with
            `full_path` and a list of signing `formats`.

    """
    filelist_dict = {}
    messages = []
    for artifact_dict in context.task["payload"]["upstreamArtifacts"]:
        authenticode_comment = artifact_dict.get("authenticode_comment")
        if authenticode_comment and not any("authenticode" in fmt for fmt in artifact_dict["formats"]):
            raise TaskVerificationError("Cannot use authenticode_comment without an authenticode format")

        if authenticode_comment and not any(path.endswith(".msi") for path in artifact_dict["paths"]):
            # Don't have to think about .zip and such unpacking for the comment
            raise TaskVerificationError("There is no support for authenticode_comment outside of msi's at this time")
        for path in artifact_dict["paths"]:
            full_path = os.path.join(context.config["work_dir"], "cot", artifact_dict["taskId"], path)
            if not os.path.exists(full_path):
                messages.append("{} doesn't exist!".format(full_path))
            filelist_dict[path] = {"full_path": full_path, "formats": _sort_formats(artifact_dict["formats"])}
            if authenticode_comment:
                filelist_dict[path]["comment"] = authenticode_comment

    if messages:
        raise TaskVerificationError(messages)
    return filelist_dict
