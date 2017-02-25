"""Signingscript task functions."""
import aiohttp
import asyncio
from asyncio.subprocess import PIPE, STDOUT
import json
import logging
import os
import random
import shutil
import tempfile
import traceback

import scriptworker.client
from scriptworker.exceptions import ScriptWorkerException
from scriptworker.utils import retry_request

from signingscript import utils
from signingscript.exceptions import SigningServerError, TaskVerificationError, FailedSubprocess

log = logging.getLogger(__name__)

_ZIP_ALIGNMENT = '4'  # Value must always be 4, based on https://developer.android.com/studio/command-line/zipalign.html


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


def task_signing_formats(task):
    """Get the list of signing formats from the task signing scopes.

    Args:
        task (dict): the task definition.

    Returns:
        list: the signing formats.
    """
    return [s.split(":")[-1] for s in task["scopes"] if
            s.startswith("project:releng:signing:format:")]


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


async def sign_file(context, from_, cert_type, signing_formats, cert, to=None):
    """Send a file to the signing server to sign, then retrieve the signed file.

    In post-signing steps, zipalign apks if applicable.

    Args:
        context (SigningContext): the signing context
        from_ (str): the source file to sign
        cert_type (str): the cert type used to find an appropriate signing server
        signing_formats (str): the formats to sign with
        cert (str): the path to the ssl cert, if applicable
        to (str, optional): the path to write the signed file to.  If None,
            overwrite `from_`.  Defaults to None.

    Raises:
        FailedSubprocess: on subprocess error while signing.
    """
    to = to or from_
    work_dir = context.config['work_dir']
    token = os.path.join(work_dir, "token")
    nonce = os.path.join(work_dir, "nonce")
    signtool = context.config['signtool']
    if not isinstance(signtool, (list, tuple)):
        signtool = [signtool]
    signing_command = signtool + ["-v", "-n", nonce, "-t", token, "-c", cert]
    for s in get_suitable_signing_servers(context.signing_servers, cert_type, signing_formats):
        signing_command.extend(["-H", s.server])
    for f in signing_formats:
        signing_command.extend(["-f", f])
    signing_command.extend(["-o", to, from_])
    await _execute_subprocess(signing_command)
    log.info('Finished signing. Starting post-signing steps...')
    await _execute_post_signing_steps(context, to)


async def _execute_post_signing_steps(context, to):
    work_dir = context.config['work_dir']
    abs_to = os.path.join(work_dir, to)

    _, file_extension = os.path.splitext(abs_to)
    if file_extension == '.apk':
        await _zip_align_apk(context, abs_to)

    log.info("SHA512SUM: %s SIGNED_FILE: %s",
             utils.get_hash(abs_to, "sha512"), to)
    log.info("SHA1SUM: %s SIGNED_FILE: %s",
             utils.get_hash(abs_to, "sha1"), to)
    log.info('Post-signing steps finished')


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
        await _execute_subprocess(zipalign_command)
        shutil.move(temp_apk_location, abs_to)

    log.info('"{}" has been zip aligned'.format(abs_to))


async def _execute_subprocess(command):
    log.info('Running "{}"'.format(' '.join(command)))
    subprocess = await asyncio.create_subprocess_exec(*command, stdout=PIPE, stderr=STDOUT)
    log.info("COMMAND OUTPUT: ")
    await utils.log_output(subprocess.stdout)
    exitcode = await subprocess.wait()
    log.info("exitcode {}".format(exitcode))

    if exitcode != 0:
        raise FailedSubprocess('Command `{}` failed'.format(' '.join(command)))


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
                "formats": artifact_dict['formats'],
            }
    if messages:
        raise TaskVerificationError(messages)
    return filelist_dict
