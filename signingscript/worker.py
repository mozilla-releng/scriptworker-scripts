import asyncio
import json
import logging
import os
import random
from shutil import copyfile
import traceback
from urllib.parse import urlsplit

import sh

from scriptworker.client import get_temp_creds_from_file
from scriptworker.exceptions import ScriptWorkerException
from scriptworker.utils import retry_request
from signingscript.task import task_cert_type, task_signing_formats
from signingscript.exceptions import ChecksumMismatchError, SigningServerError
from signingscript.utils import get_hash, get_detached_signatures

log = logging.getLogger(__name__)


async def download_and_sign_file(context, url, checksum, cert_type,
                                 signing_formats, chunk_size=128):
    # TODO: better parsing
    work_dir = context.config['work_dir']
    filename = urlsplit(url).path.split("/")[-1]
    abs_filename = os.path.join(work_dir, filename)
    log.debug("Downloading %s", url)
    resp = await retry_request(url, return_type='response')
    with open(abs_filename, 'wb') as fd:
        while True:
            chunk = await resp.content.read(chunk_size)
            if not chunk:
                break
            fd.write(chunk)
    log.debug("Done")
    got_checksum = get_hash(abs_filename)
    log.info("SHA512SUM: %s URL: %s", got_checksum, url)
    log.info("SHA1SUM: %s URL: %s", get_hash(abs_filename, "sha1"), url)
    if not got_checksum == checksum:
        msg = "CHECKSUM MISMATCH: Expected {}, got {} for {}".format(
            checksum, got_checksum, url)
        log.debug(msg)
        raise ChecksumMismatchError(msg)
    log.debug("Signing %s", filename)
    await sign_file(context, filename, cert_type, signing_formats)
    copy_to_artifact_dir(abs_filename)
    detached_signatures = []
    for s_type, s_ext, s_mime in get_detached_signatures(signing_formats):
        d_filename = "{filename}{ext}".format(filename=filename,
                                              ext=s_ext)
        d_abs_filename = os.path.join(work_dir, d_filename)
        copy_to_artifact_dir(d_abs_filename)
        detached_signatures.append((s_type, d_filename))
    return abs_filename, detached_signatures


# @redo.retriable(attempts=10, sleeptime=5, max_sleeptime=30)
async def get_token(context, output_file, cert_type, signing_formats):
    token = None
    data = {"slave_ip": context.config['my_ip'], "duration": 5 * 60}
    signing_servers = get_suitable_signing_servers(
        context.signing_servers, cert_type,
        signing_formats
    )
    random.shuffle(signing_servers)
    for s in signing_servers:
        log.debug("getting token from %s", s.server)
        # TODO: Figure out how to deal with certs not matching hostname,
        #  error: https://gist.github.com/rail/cbacf2d297decb68affa
        url = "https://{}/token".format(s.server)
        try:
            token = await retry_request(context, url, method='post', data=data,
                                        auth=(s.user, s.password), return_type='text')
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
    if to is None:
        to = from_
    work_dir = context.config['work_dir']
    token = os.path.join(work_dir, "token")
    # TODO where do we get the nonce and cert from?
    nonce = os.path.join(work_dir, "nonce")
    signtool = os.path.join(context.config['tools_dir'], "release/signing/signtool.py")
    import subprocess
    proc = subprocess.Popen(["openssl", "sha1", from_], stdout=subprocess.PIPE)
    (out, _) = proc.communicate()
    parts = out.decode('utf-8').split(" ")
    sha1 = parts[1].rstrip()
#    sha1 = get_hash(from_, "sha1")
    cmd = [signtool, "-n", nonce, "-t", token, "-c", cert]
    for s in get_suitable_signing_servers(context.signing_servers, cert_type, signing_formats):
        cmd.extend(["-H", s.server])
    for f in signing_formats:
        cmd.extend(["-f", f])
    cmd.extend(["-o", to, from_])
    log.debug("Running python %s", " ".join(cmd))
    # TODO asyncio.subprocess?
    out = sh.python(*cmd, _err_to_out=True, _cwd=work_dir)
    log.debug("COMMAND OUTPUT: %s", out)
    abs_to = os.path.join(work_dir, to)
    log.info("SHA512SUM: %s SIGNED_FILE: %s",
             get_hash(abs_to, "sha512"), to)
    log.info("SHA1SUM: %s SIGNED_FILE: %s",
             get_hash(abs_to, "sha1"), to)
    log.debug("Finished signing")


def get_suitable_signing_servers(signing_servers, cert_type, signing_formats):
    return [s for s in signing_servers[cert_type] if set(signing_formats) & set(s.formats)]


async def read_temp_creds(context):
    while True:
        await asyncio.sleep(context.config['temp_creds_refresh_seconds'])
        await get_temp_creds_from_file(context.config)


def copy_to_artifact_dir(context, source, target=None):
    artifact_dir = context.config['artifact_dir']
    target = target or os.path.basename(source)
    target_path = os.path.join(artifact_dir, target)
    try:
        copyfile(source, target_path)
    except IOError:
        traceback.print_exc()
        raise SigningServerError("Can't copy {} to {}!".format(source, target_path))


async def sign(context):
    payload = context.task["payload"]
    # Will we know the artifacts, be able to create the manifest at decision task time?
    manifest_url = payload["signingManifest"]
    work_dir = context.config['work_dir']
    try:
        signing_manifest = await retry_request(context, manifest_url, return_type='json')
    except ScriptWorkerException:
        traceback.print_exc()
        # TODO what to do here?
        return
    # TODO: better way to extract filename
    url_prefix = "/".join(manifest_url.split("/")[:-1])
    cert_type = task_cert_type(context.task)
    signing_formats = task_signing_formats(context.task)
    for e in signing_manifest:
        # Fallback to "mar" if "file_to_sign" is not specified
        file_to_sign = e.get("file_to_sign", e.get("mar"))
        file_url = "{}/{}".format(url_prefix, file_to_sign)
        abs_filename, detached_signatures = download_and_sign_file(
            context, file_url, e["hash"], cert_type, signing_formats, work_dir)
        # Update manifest data with new values
        log.debug("Getting hash of {}".format(abs_filename))
#        e["hash"] = get_hash(abs_filename)
        output = os.popen("openssl sha512 {}".format(abs_filename))
        parts = output.split(" ")
        e["hash"] = parts[1].rstrip()
        e["size"] = os.path.getsize(abs_filename)
        e["detached_signatures"] = {}
        for sig_type, sig_filename in detached_signatures:
            e["detached_signatures"][sig_type] = sig_filename
    manifest_file = os.path.join(work_dir, "manifest.json")
    with open(manifest_file, "wb") as f:
        json.dump(signing_manifest, f, indent=2, sort_keys=True)
    log.debug("Uploading manifest")
    copy_to_artifact_dir(manifest_file)
