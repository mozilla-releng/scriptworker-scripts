#!/usr/bin/env python
"""Signingscript task functions."""
import asyncio
import difflib
import fnmatch
import glob
import logging
import os
import re
import shutil
import tarfile
import tempfile
import zipfile

from scriptworker.utils import makedirs, raise_future_exceptions, rm, get_single_item_from_sequence

from signingscript import utils
from signingscript.createprecomplete import generate_precomplete
from signingscript.exceptions import SigningScriptError

log = logging.getLogger(__name__)

_ZIP_ALIGNMENT = '4'  # Value must always be 4, based on https://developer.android.com/studio/command-line/zipalign.html

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


# build_signtool_cmd {{{1
def build_signtool_cmd(context, from_, fmt, to=None):
    """Generate a signtool command to run.

    Args:
        context (Context): the signing context
        from_ (str): the source file to sign
        fmt (str): the format to sign with
        to (str, optional): the target path to sign to. If None, overwrite
            `from_`. Defaults to None.

    Returns:
        list: the signtool command to run.

    """
    to = to or from_
    work_dir = context.config['work_dir']
    token = os.path.join(work_dir, "token")
    nonce = os.path.join(work_dir, "nonce")
    from signingscript.task import task_cert_type
    cert_type = task_cert_type(context)
    ssl_cert = context.config['ssl_cert']
    signtool = context.config['signtool']
    if not isinstance(signtool, (list, tuple)):
        signtool = [signtool]
    cmd = signtool + ["-v", "-n", nonce, "-t", token, "-c", ssl_cert]
    for s in get_suitable_signing_servers(
        context.signing_servers, cert_type, [fmt]
    ):
        cmd.extend(["-H", s.server])
    cmd.extend(["-f", fmt])
    cmd.extend(["-o", to, from_])
    return cmd


# sign_file {{{1
async def sign_file(context, from_, fmt, to=None):
    """Send the file to signtool to be signed.

    Args:
        context (Context): the signing context
        from_ (str): the source file to sign
        fmt (str): the format to sign with
        to (str, optional): the target path to sign to. If None, overwrite
            `from_`. Defaults to None.

    Raises:
        FailedSubprocess: on subprocess error while signing.

    Returns:
        str: the path to the signed file

    """
    log.info("sign_file(): signing {} with {}...".format(from_, fmt))
    cmd = build_signtool_cmd(context, from_, fmt, to=to)
    await utils.execute_subprocess(cmd)
    return to or from_


# sign_gpg {{{1
async def sign_gpg(context, from_, fmt):
    """Create a detached armored signature with the gpg key.

    Because this function returns a list, gpg must be the final signing format.

    Args:
        context (Context): the signing context
        from_ (str): the source file to sign
        fmt (str): the format to sign with

    Returns:
        list: the path to the signed file, and sig.

    """
    to = "{}.asc".format(from_)
    await sign_file(context, from_, fmt, to=to)
    return [from_, to]


# sign_jar {{{1
async def sign_jar(context, from_, fmt):
    """Sign an apk, and zipalign.

    Args:
        context (Context): the signing context
        from_ (str): the source file to sign
        fmt (str): the format to sign with

    Returns:
        str: the path to the signed file

    """
    await sign_file(context, from_, fmt)
    await zip_align_apk(context, from_)
    return from_


# sign_macapp {{{1
async def sign_macapp(context, from_, fmt):
    """Sign a macapp.

    If given a dmg, convert to a tar.gz file first, then sign the internals.

    Args:
        context (Context): the signing context
        from_ (str): the source file to sign
        fmt (str): the format to sign with

    Returns:
        str: the path to the signed file

    """
    file_base, file_extension = os.path.splitext(from_)
    if file_extension == '.dmg':
        await _convert_dmg_to_tar_gz(context, from_)
        from_ = "{}.tar.gz".format(file_base)
    await sign_file(context, from_, fmt)
    return from_


# sign_signcode {{{1
async def sign_signcode(context, orig_path, fmt):
    """Sign a zipfile with authenticode.

    Extract the zip and only sign unsigned files that don't match certain
    patterns (see `_should_sign_windows`). Then recreate the zip.

    Args:
        context (Context): the signing context
        orig_path (str): the source file to sign
        fmt (str): the format to sign with

    Returns:
        str: the path to the signed zip

    """
    file_base, file_extension = os.path.splitext(orig_path)
    # This will get cleaned up when we nuke `work_dir`. Clean up at that point
    # rather than immediately after `sign_signcode`, to optimize task runtime
    # speed over disk space.
    tmp_dir = None
    # Extract the zipfile
    if file_extension == '.zip':
        tmp_dir = tempfile.mkdtemp(prefix="zip", dir=context.config['work_dir'])
        files = await _extract_zipfile(context, orig_path, tmp_dir=tmp_dir)
    else:
        files = [orig_path]
    # Sign the appropriate inner files
    for from_ in files:
        if _should_sign_windows(from_):
            await sign_file(context, from_, fmt)
    if file_extension == '.zip':
        # Recreate the zipfile
        await _create_zipfile(context, orig_path, files, tmp_dir=tmp_dir)
    return orig_path


# sign_widevine {{{1
async def sign_widevine(context, orig_path, fmt):
    """Call the appropriate helper function to do widevine signing.

    Args:
        context (Context): the signing context
        orig_path (str): the source file to sign
        fmt (str): the format to sign with

    Raises:
        SigningScriptError: on unknown suffix.

    Returns:
        str: the path to the signed archive

    """
    file_base, file_extension = os.path.splitext(orig_path)
    # Convert dmg to tarball
    if file_extension == '.dmg':
        await _convert_dmg_to_tar_gz(context, orig_path)
        orig_path = "{}.tar.gz".format(file_base)
    ext_to_fn = {
        '.zip': sign_widevine_zip,
        '.tar.bz2': sign_widevine_tar,
        '.tar.gz': sign_widevine_tar,
    }
    for ext, signing_func in ext_to_fn.items():
        if orig_path.endswith(ext):
            return await signing_func(context, orig_path, fmt)
    raise SigningScriptError(
        "Unknown widevine file format for {}".format(orig_path)
    )


# sign_widevine_zip {{{1
async def sign_widevine_zip(context, orig_path, fmt):
    """Sign the internals of a zipfile with the widevine key.

    Extract the files to sign (see `_WIDEVINE_BLESSED_FILENAMES` and
    `_WIDEVINE_UNBLESSED_FILENAMES), skipping already-signed files.
    The blessed files should be signed with the `widevine_blessed` format.
    Then append the sigfiles to the zipfile.

    Args:
        context (Context): the signing context
        orig_path (str): the source file to sign
        fmt (str): the format to sign with

    Returns:
        str: the path to the signed archive

    """
    # This will get cleaned up when we nuke `work_dir`. Clean up at that point
    # rather than immediately after `sign_widevine`, to optimize task runtime
    # speed over disk space.
    tmp_dir = tempfile.mkdtemp(prefix="wvzip", dir=context.config['work_dir'])
    # Get file list
    all_files = await _get_zipfile_files(orig_path)
    files_to_sign = _get_widevine_signing_files(all_files)
    log.debug("Widevine files to sign: {}".format(files_to_sign))
    if files_to_sign:
        # Extract all files so we can create `precomplete` with the full
        # file list
        all_files = await _extract_zipfile(context, orig_path, tmp_dir=tmp_dir)
        tasks = []
        # Sign the appropriate inner files
        for from_, fmt in files_to_sign.items():
            from_ = os.path.join(tmp_dir, from_)
            to = "{}.sig".format(from_)
            tasks.append(asyncio.ensure_future(sign_file(
                context, from_, fmt, to=to
            )))
            all_files.append(to)
        await raise_future_exceptions(tasks)
        remove_extra_files(tmp_dir, all_files)
        # Regenerate the `precomplete` file, which is used for cleanup before
        # applying a complete mar.
        _run_generate_precomplete(context, tmp_dir)
        await _create_zipfile(
            context, orig_path, all_files, mode='w', tmp_dir=tmp_dir
        )
    return orig_path


# sign_widevine_tar {{{1
async def sign_widevine_tar(context, orig_path, fmt):
    """Sign the internals of a tarfile with the widevine key.

    Extract the entire tarball, but only sign a handful of files (see
    `_WIDEVINE_BLESSED_FILENAMES` and `_WIDEVINE_UNBLESSED_FILENAMES).
    The blessed files should be signed with the `widevine_blessed` format.
    Then recreate the tarball.

    Ideally we would be able to append the sigfiles to the original tarball,
    but that's not possible with compressed tarballs.

    Args:
        context (Context): the signing context
        orig_path (str): the source file to sign
        fmt (str): the format to sign with

    Returns:
        str: the path to the signed archive

    """
    _, compression = os.path.splitext(orig_path)
    # This will get cleaned up when we nuke `work_dir`. Clean up at that point
    # rather than immediately after `sign_widevine`, to optimize task runtime
    # speed over disk space.
    tmp_dir = tempfile.mkdtemp(prefix="wvtar", dir=context.config['work_dir'])
    # Get file list
    all_files = await _get_tarfile_files(orig_path, compression)
    files_to_sign = _get_widevine_signing_files(all_files)
    log.debug("Widevine files to sign: {}".format(files_to_sign))
    if files_to_sign:
        # Extract all files so we can create `precomplete` with the full
        # file list
        all_files = await _extract_tarfile(
            context, orig_path, compression, tmp_dir=tmp_dir
        )
        tasks = []
        # Sign the appropriate inner files
        for from_, fmt in files_to_sign.items():
            from_ = os.path.join(tmp_dir, from_)
            # Don't try to sign directories
            if not os.path.isfile(from_):
                continue
            # Move the sig location on mac. This should be noop on linux.
            to = _get_mac_sigpath(from_)
            log.debug("Adding {} to the sigfile paths...".format(to))
            makedirs(os.path.dirname(to))
            tasks.append(asyncio.ensure_future(sign_file(
                context, from_, fmt, to=to
            )))
            all_files.append(to)
        await raise_future_exceptions(tasks)
        remove_extra_files(tmp_dir, all_files)
        # Regenerate the `precomplete` file, which is used for cleanup before
        # applying a complete mar.
        _run_generate_precomplete(context, tmp_dir)
        await _create_tarfile(
            context, orig_path, all_files, compression, tmp_dir=tmp_dir
        )
    return orig_path


# _should_sign_windows {{{1
def _should_sign_windows(filename):
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
        return True
    return False


# _get_mac_sigpath {{{1
def _get_mac_sigpath(from_):
    """For mac paths, replace the final Contents/MacOS/ with Contents/Resources/."""
    to = from_
    if 'Contents/MacOS' in from_:
        parts = from_.split('/')
        parts.reverse()
        i = parts.index('MacOS')
        parts[i] = "Resources"
        parts.reverse()
        to = '/'.join(parts)
        log.debug("Sigfile for {} should be {}.sig".format(from_, to))
    return "{}.sig".format(to)


# _get_widevine_signing_files {{{1
def _get_widevine_signing_files(file_list):
    """Return a dict of path:signing_format for each path to be signed."""
    files = {}
    for filename in file_list:
        fmt = None
        base_filename = os.path.basename(filename)
        if base_filename in _WIDEVINE_BLESSED_FILENAMES:
            fmt = 'widevine_blessed'
        elif base_filename in _WIDEVINE_NONBLESSED_FILENAMES:
            fmt = 'widevine'
        if fmt:
            log.debug("Found {} to sign {}".format(filename, fmt))
            sigpath = _get_mac_sigpath(filename)
            if sigpath not in file_list:
                files[filename] = fmt
            else:
                log.debug("{} is already signed! Skipping...".format(filename))
    return files


# _run_generate_precomplete {{{1
def _run_generate_precomplete(context, tmp_dir):
    """Regenerate `precomplete` file with widevine sig paths for complete mar."""
    log.info("Generating `precomplete` file...")
    path = _ensure_one_precomplete(tmp_dir, "before")
    with open(path, "r") as fh:
        before = fh.readlines()
    generate_precomplete(os.path.dirname(path))
    path = _ensure_one_precomplete(tmp_dir, "after")
    with open(path, "r") as fh:
        after = fh.readlines()
    # Create diff file
    diff_path = os.path.join(context.config['work_dir'], "precomplete.diff")
    with open(diff_path, "w") as fh:
        for line in difflib.ndiff(before, after):
            fh.write(line)
    utils.copy_to_dir(
        diff_path, context.config['artifact_dir'],
        target="public/logs/precomplete.diff"
    )


# _ensure_one_precomplete {{{1
def _ensure_one_precomplete(tmp_dir, adj):
    """Ensure we only have one `precomplete` file in `tmp_dir`."""
    return get_single_item_from_sequence(
        glob.glob(os.path.join(tmp_dir, '**', 'precomplete'), recursive=True),
        condition=lambda _: True,
        ErrorClass=SigningScriptError,
        no_item_error_message='No `precomplete` file found in "{}"'.format(tmp_dir),
        too_many_item_error_message='More than one `precomplete` file {} in "{}"'.format(adj, tmp_dir),
    )


# remove_extra_files {{{1
def remove_extra_files(top_dir, file_list):
    """Find any extra files in `top_dir`, given an expected `file_list`.

    Args:
        top_dir (str): the dir to walk
        file_list (list): the list of expected files

    Returns:
        list: the list of extra files

    """
    all_files = [os.path.realpath(f) for f in glob.glob(os.path.join(top_dir, '**', '*'), recursive=True)]
    good_files = [os.path.realpath(f) for f in file_list]
    extra_files = list(set(all_files) - set(good_files))
    for f in extra_files:
        if os.path.isfile(f):
            log.warning("Extra file to clean up: {}".format(f))
            rm(f)
    return extra_files


# zip_align_apk {{{1
async def zip_align_apk(context, abs_to):
    """Optimize APK for better run-time performance.

    This is necessary if the APK is uploaded to the Google Play Store.
    https://developer.android.com/studio/command-line/zipalign.html

    Args:
        context (Context): the signing context
        abs_to (str): the absolute path to the apk

    """
    original_apk_location = abs_to
    zipalign_executable_location = context.config['zipalign']

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_apk_location = os.path.join(temp_dir, 'aligned.apk')

        zipalign_command = [zipalign_executable_location]
        if context.config['verbose'] is True:
            zipalign_command += ['-v']

        zipalign_command += [_ZIP_ALIGNMENT, original_apk_location, temp_apk_location]
        await utils.execute_subprocess(zipalign_command)
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
        await utils.execute_subprocess(undmg_cmd, cwd=temp_dir)
        hfsplus_cmd = [hfsplus_executable_location, "tmp.hfs", "extractall", "/", app_dir]
        await utils.execute_subprocess(hfsplus_cmd, cwd=temp_dir)
        tar_cmd = ['tar', 'czvf', abs_to, '.']
        await utils.execute_subprocess(tar_cmd, cwd=app_dir)

    return to


# _get_zipfile_files {{{1
async def _get_zipfile_files(from_):
    with zipfile.ZipFile(from_, mode='r') as z:
        files = z.namelist()
        return files


# _extract_zipfile {{{1
async def _extract_zipfile(context, from_, files=None, tmp_dir=None):
    work_dir = context.config['work_dir']
    tmp_dir = tmp_dir or os.path.join(work_dir, "unzipped")
    log.debug("Extracting {} from {} to {}...".format(
        files or "all files", from_, tmp_dir
    ))
    try:
        extracted_files = []
        rm(tmp_dir)
        utils.mkdir(tmp_dir)
        with zipfile.ZipFile(from_, mode='r') as z:
            if files is not None:
                for name in files:
                    z.extract(name, path=tmp_dir)
                    extracted_files.append(os.path.join(tmp_dir, name))
            else:
                for name in z.namelist():
                    extracted_files.append(os.path.join(tmp_dir, name))
                z.extractall(path=tmp_dir)
        return extracted_files
    except Exception as e:
        raise SigningScriptError(e)


# _create_zipfile {{{1
async def _create_zipfile(context, to, files, tmp_dir=None, mode='w'):
    work_dir = context.config['work_dir']
    tmp_dir = tmp_dir or os.path.join(work_dir, "unzipped")
    try:
        log.info("Creating zipfile {}...".format(to))
        with zipfile.ZipFile(to, mode=mode, compression=zipfile.ZIP_DEFLATED) as z:
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


# _get_tarfile_files {{{1
async def _get_tarfile_files(from_, compression):
    compression = _get_tarfile_compression(compression)
    with tarfile.open(from_, mode='r:{}'.format(compression)) as t:
        files = t.getnames()
        return files


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
                os.path.isfile(path) and files.append(path)
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
