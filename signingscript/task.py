#!/usr/bin/env python
"""Signingscript task functions."""
import aiohttp
import fnmatch
import json
import logging
import os
import random
import re
import shutil
import tarfile
import tempfile
import traceback
import zipfile

import scriptworker.client
from scriptworker.exceptions import ScriptWorkerException
from scriptworker.utils import retry_request, rm

from signingscript import utils
from signingscript.exceptions import SigningScriptError, SigningServerError, TaskVerificationError

log = logging.getLogger(__name__)

_ZIP_ALIGNMENT = '4'  # Value must always be 4, based on https://developer.android.com/studio/command-line/zipalign.html

# These are the signing formats where we might extract a zipfile's contents
# before signing.
_ZIPFILE_SIGNING_FORMATS = frozenset(['sha2signcode', 'signcode', 'osslsigncode'])

# Widevine settings.
_WIDEVINE_SIGNING_FORMATS = ('widevine', 'widevine_blessed')
# Blessed files call the other widevine files.
_WIDEVINE_BLESSED_FILENAMES = (
    # plugin-container is the top of the calling stack
    "plugin-container",
    "plugin-container.exe",
)
# These are other files that need to be widevine-signed
_WIDEVINE_NONBLESSED_FILENAMES = (
    # firefox
    "firefox",
    "firefox-bin",
    "firefox.exe",
    # xul
    "libxul.so",
    "XUL",
    "xul.dll",
    # clearkey for regression testing.
    "clearkey.dll",
    "libclearkey.dylib",
    "libclearkey.so",
)


# task_cert_type {{{1
def task_cert_type(task):
    """Extract task certificate type.

    Args:
        task (dict): the task definition.

    Raises:
        TaskVerificationError: if the number of cert scopes is not 1.

    Returns:
        str: the cert type.

    """
    certs = [s for s in task["scopes"] if
             s.startswith("project:releng:signing:cert:")]
    log.info("Certificate types: %s", certs)
    if len(certs) != 1:
        raise TaskVerificationError("Only one certificate type can be used")
    return certs[0]


# task_signing_formats {{{1
def task_signing_formats(task):
    """Get the list of signing formats from the task signing scopes.

    Args:
        task (dict): the task definition.

    Returns:
        list: the signing formats.

    """
    return [s.split(":")[-1] for s in task["scopes"] if
            s.startswith("project:releng:signing:format:")]


# validate_task_schema {{{1
def validate_task_schema(context):
    """Validate the task json schema.

    Args:
        context (SigningContext): the signing context.

    Raises:
        ScriptWorkerTaxkException: on failed validation.

    """
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)


# get_suitable_signing_servers {{{1
def get_suitable_signing_servers(signing_servers, cert_type, signing_formats):
    """Get the list of signing servers for given `signing_formats` and `cert_type`.

    Args:
        signing_servers (dict of lists of lists): the contents of
            `signing_server_config`.
        cert_type (str): the certificate type - essentially signing level,
            separating release vs nightly vs dep.
        signing_formats (list): the signing formats the server needs to support

    Returns:
        list of lists: the list of signing servers.

    """
    return [s for s in signing_servers[cert_type] if set(signing_formats) & set(s.formats)]


# get_token {{{1
async def get_token(context, output_file, cert_type, signing_formats):
    """Retrieve a token from the signingserver tied to my ip.

    Args:
        context (SigningContext): the signing context
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


# sign_file {{{1
async def sign_file(context, orig_file, cert_type, signing_formats, cert):
    """Send a file to the signing server to sign, then retrieve the signed file.

    In post-signing steps, zipalign apks if applicable.

    Args:
        context (SigningContext): the signing context
        orig_file (str): the source file to sign
        cert_type (str): the cert type used to find an appropriate signing server
        signing_formats (str): the formats to sign with
        cert (str): the path to the ssl cert, if applicable

    Raises:
        FailedSubprocess: on subprocess error while signing.

    """
    work_dir = context.config['work_dir']
    token = os.path.join(work_dir, "token")
    nonce = os.path.join(work_dir, "nonce")
    signtool = context.config['signtool']
    if not isinstance(signtool, (list, tuple)):
        signtool = [signtool]
    signed_file = orig_file
    # Loop through the formats and sign one by one.
    for orig_fmt in signing_formats:
        signed_file, files, should_sign_fn = await _execute_pre_signing_steps(context, signed_file, orig_fmt)
        for from_ in files:
            to = from_
            fmt = orig_fmt
            # build the base command
            if should_sign_fn is not None:
                fmt = should_sign_fn(from_, orig_fmt)
            if not fmt:
                continue
            # widevine has a detached sig for the inner files, but not for the
            # final file, so we can't use DETACHED_SIGNATURES here
            elif fmt in ("widevine", "widevine_blessed"):
                to = "{}.sig".format(from_)
                if to not in files:
                    files.append(to)
            else:
                to = from_
            log.info("Signing {}...".format(from_))
            base_command = signtool + ["-v", "-n", nonce, "-t", token, "-c", cert]
            for s in get_suitable_signing_servers(context.signing_servers, cert_type, [fmt]):
                base_command.extend(["-H", s.server])
            base_command.extend(["-f", fmt])
            signing_command = base_command[:]
            signing_command.extend(["-o", to, from_])
            await utils._execute_subprocess(signing_command)
        log.info('Finished signing {}. Starting post-signing steps...'.format(orig_fmt))
        signed_file = await _execute_post_signing_steps(context, files, signed_file, orig_fmt)
    return signed_file


# _should_sign_windows {{{1
def _should_sign_windows(filename, fmt):
    """Return True if filename should be signed."""
    # These should already be signed by Microsoft.
    _dont_sign = [
        'D3DCompiler_42.dll', 'd3dx9_42.dll',
        'D3DCompiler_43.dll', 'd3dx9_43.dll',
        'msvc*.dll',
    ]
    ext = os.path.splitext(filename)[1]
    b = os.path.basename(filename)
    if ext in ('.dll', '.exe') and not any(fnmatch.fnmatch(b, p) for p in _dont_sign):
        return fmt
    return False


# _should_sign_widevine {{{1
def _should_sign_widevine(filename, fmt):
    """Return (True, blessed) if filename should be signed."""
    base_filename = os.path.basename(filename)
    if base_filename in _WIDEVINE_BLESSED_FILENAMES:
        return "widevine_blessed"
    elif base_filename in _WIDEVINE_NONBLESSED_FILENAMES:
        return "widevine"


# _execute_pre_signing_steps {{{1
async def _execute_pre_signing_steps(context, from_, fmt):
    """Execute pre-signing steps for these file(s) and format.

    Returns a list of files, and a callback that specifies which files to sign

    """
    file_base, file_extension = os.path.splitext(from_)
    callback = None
    if file_extension == '.dmg':
        await _convert_dmg_to_tar_gz(context, from_)
        from_ = "{}.tar.gz".format(file_base)
    # XXX staging do not land the next 3 lines
        file_base, file_extension = os.path.splitext(from_)
    # elif file_extension == '.zip' and fmt in _ZIPFILE_SIGNING_FORMATS:
    if file_extension == '.zip' and fmt in _ZIPFILE_SIGNING_FORMATS:
        return (from_, await _extract_zipfile(context, from_), _should_sign_windows)
    elif fmt in _WIDEVINE_SIGNING_FORMATS:
        if file_base.endswith('.tar'):
            return (
                from_,
                await _extract_tarfile(
                    context, from_, compression=file_extension
                ),
                _should_sign_widevine
            )
        elif file_extension == '.zip':
            return (from_, await _extract_zipfile(context, from_), _should_sign_widevine)
        else:
            # we should never hit this
            raise SigningScriptError("Unknown file suffix for widevine signing: {}".format(from_))

    return (from_, [from_], callback)


# _execute_post_signing_steps {{{1
async def _execute_post_signing_steps(context, files, orig_file, fmt):
    work_dir = context.config['work_dir']

    file_base, file_extension = os.path.splitext(orig_file)
    # Re-zip unzipped files
    if file_extension == '.zip' and fmt in _ZIPFILE_SIGNING_FORMATS:
        signed_file = await _create_zipfile(context, os.path.join(work_dir, orig_file), files)
    elif fmt in _WIDEVINE_SIGNING_FORMATS:
        if file_extension == '.zip':
            signed_file = await _create_zipfile(context, os.path.join(work_dir, orig_file), files)
        if file_base.endswith('.tar'):
            signed_file = await _create_tarfile(
                context, os.path.join(work_dir, orig_file), files,
                compression=file_extension
            )
    else:
        # We should never hit this, but just in case:
        if len(files) != 1:
            raise SigningScriptError("Unexpected number of files for non-zip: {}".format(files))
        signed_file = os.path.join(work_dir, files[0])
        # Zipalign apks
        if file_extension == '.apk':
            await _zip_align_apk(context, signed_file)

    rel_signed_file = os.path.relpath(signed_file, work_dir)
    log.info("SHA512SUM: %s SIGNED_FILE: %s",
             utils.get_hash(signed_file, "sha512"), rel_signed_file)
    log.info("SHA1SUM: %s SIGNED_FILE: %s",
             utils.get_hash(signed_file, "sha1"), rel_signed_file)
    log.info('Post-signing steps finished')
    return signed_file


# _zip_align_apk {{{1
async def _zip_align_apk(context, abs_to):
    """Replace APK with a zip aligned one."""
    original_apk_location = abs_to
    zipalign_executable_location = context.config['zipalign']

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_apk_location = os.path.join(temp_dir, 'aligned.apk')

        zipalign_command = [zipalign_executable_location]
        if context.config['verbose'] is True:
            zipalign_command += ['-v']

        zipalign_command += [_ZIP_ALIGNMENT, original_apk_location, temp_apk_location]
        await utils._execute_subprocess(zipalign_command)
        shutil.move(temp_apk_location, abs_to)

    log.info('"{}" has been zip aligned'.format(abs_to))


# _convert_dmg_to_tar_gz {{{1
async def _convert_dmg_to_tar_gz(context, from_):
    """Explode a dmg and tar up its contents. Return the relative tarball path."""
    work_dir = context.config['work_dir']
    abs_from = os.path.join(work_dir, from_)
    # replace .dmg suffix with .tar.gz (case insensitive)
    to = re.sub('\.dmg$', '.tar.gz', from_, flags=re.I)
    abs_to = os.path.join(work_dir, to)
    dmg_executable_location = context.config['dmg']
    hfsplus_executable_location = context.config['hfsplus']

    with tempfile.TemporaryDirectory() as temp_dir:
        app_dir = os.path.join(temp_dir, "app")
        utils.mkdir(app_dir)
        undmg_cmd = [dmg_executable_location, "extract", abs_from, "tmp.hfs"]
        await utils._execute_subprocess(undmg_cmd, cwd=temp_dir)
        hfsplus_cmd = [hfsplus_executable_location, "tmp.hfs", "extractall", "/", app_dir]
        await utils._execute_subprocess(hfsplus_cmd, cwd=temp_dir)
        tar_cmd = ['tar', 'czvf', abs_to, '.']
        await utils._execute_subprocess(tar_cmd, cwd=app_dir)

    return to


# _extract_zipfile {{{1
async def _extract_zipfile(context, from_, tmp_dir=None):
    work_dir = context.config['work_dir']
    tmp_dir = tmp_dir or os.path.join(work_dir, "unzipped")
    try:
        files = []
        rm(tmp_dir)
        utils.mkdir(tmp_dir)
        with zipfile.ZipFile(from_, mode='r') as z:
            for name in z.namelist():
                files.append(os.path.join(tmp_dir, name))
            z.extractall(path=tmp_dir)
        return files
    except Exception as e:
        raise SigningScriptError(e)


# _create_zipfile {{{1
async def _create_zipfile(context, to, files, tmp_dir=None):
    work_dir = context.config['work_dir']
    tmp_dir = tmp_dir or os.path.join(work_dir, "unzipped")
    try:
        log.info("Creating zipfile {}...".format(to))
        with zipfile.ZipFile(to, mode='w', compression=zipfile.ZIP_DEFLATED) as z:
            for f in files:
                relpath = os.path.relpath(f, tmp_dir)
                z.write(f, arcname=relpath)
        return to
    except Exception as e:
        raise SigningScriptError(e)


# _get_tarfile_compression {{{1
def _get_tarfile_compression(compression):
    compression = compression.lstrip('.')
    if compression not in ('bz2', 'gz'):
        raise SigningScriptError(
            "{} not a supported tarfile compression format!".format(compression)
        )
    return compression


# _extract_tarfile {{{1
async def _extract_tarfile(context, from_, compression, tmp_dir=None):
    work_dir = context.config['work_dir']
    tmp_dir = tmp_dir or os.path.join(work_dir, "untarred")
    compression = _get_tarfile_compression(compression)
    try:
        files = []
        rm(tmp_dir)
        utils.mkdir(tmp_dir)
        with tarfile.open(from_, mode='r:{}'.format(compression)) as t:
            t.extractall(path=tmp_dir)
            for name in t.getnames():
                path = os.path.join(tmp_dir, name)
                if os.path.isfile(path):
                    files.append(path)
        return files
    except Exception as e:
        raise SigningScriptError(e)


# _create_tarfile {{{1
async def _create_tarfile(context, to, files, compression, tmp_dir=None):
    work_dir = context.config['work_dir']
    tmp_dir = tmp_dir or os.path.join(work_dir, "untarred")
    compression = _get_tarfile_compression(compression)
    try:
        log.info("Creating tarfile {}...".format(to))
        with tarfile.open(to, mode='w:{}'.format(compression)) as t:
            for f in files:
                relpath = os.path.relpath(f, tmp_dir)
                t.add(f, arcname=relpath)
        return to
    except Exception as e:
        raise SigningScriptError(e)


# detached_sigfiles {{{1
def detached_sigfiles(filepath, signing_formats):
    """Get a list of detached sigfile paths, if any, given a file path and signing formats.

    This will generally be an empty list unless we're gpg signing, in which case
    we'll have detached gpg signatures.

    Args:
        filepath (str): the path of the file to sign
        signing_formats (str): the signing formats the file will be signed with

    Returns:
        list: the list of paths of any detached signatures.

    """
    detached_signatures = []
    for sig_type, sig_ext, sig_mime in utils.get_detached_signatures(signing_formats):
        detached_filepath = "{filepath}{ext}".format(filepath=filepath,
                                                     ext=sig_ext)
        detached_signatures.append(detached_filepath)
    return detached_signatures


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
    for fmt in ("widevine", "widevine_blessed", "gpg"):
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
        context (SigningContext): the signing context
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
