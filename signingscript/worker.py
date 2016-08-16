import aiohttp
import asyncio
from asyncio.subprocess import PIPE, STDOUT
import logging
import os
import random
from six.moves.urllib import urlparse
import traceback

from scriptworker.exceptions import ScriptWorkerException
from scriptworker.utils import retry_async, retry_request
from signingscript.exceptions import ChecksumMismatchError, SigningServerError
from signingscript.utils import download_file, get_hash, get_detached_signatures, log_output, raise_future_exceptions

log = logging.getLogger(__name__)


async def verify_checksum(context, abs_filename, checksum):
    got_checksum = get_hash(abs_filename, "sha512")
    log.info("SHA512SUM: %s file: %s", got_checksum, abs_filename)
    log.info("SHA1SUM: %s file: %s", get_hash(abs_filename, "sha1"), abs_filename)
    if not got_checksum == checksum:
        msg = "CHECKSUM MISMATCH: Expected {}, got {} for {}".format(
            checksum, got_checksum, abs_filename)
        log.error(msg)
        raise ChecksumMismatchError(msg)


def detached_sigfiles(filename, signing_formats):
    detached_signatures = []
    for sig_type, sig_ext, sig_mime in get_detached_signatures(signing_formats):
        detached_filename = "{filename}{ext}".format(filename=filename,
                                                     ext=sig_ext)
        detached_signatures.append((sig_type, detached_filename))
    return detached_signatures


async def get_token(context, output_file, cert_type, signing_formats):
    token = None
    data = {"slave_ip": context.config['my_ip'], "duration": 10 * 60}
    signing_servers = get_suitable_signing_servers(
        context.signing_servers, cert_type,
        signing_formats
    )
    random.shuffle(signing_servers)
    for s in signing_servers:
        log.info("getting token from %s", s.server)
        # TODO: Figure out how to deal with certs not matching hostname,
        #  error: https://gist.github.com/rail/cbacf2d297decb68affa
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
    if to is None:
        to = from_
    work_dir = context.config['work_dir']
    token = os.path.join(work_dir, "token")
    nonce = os.path.join(work_dir, "nonce")
    signtool = context.config['signtool']
    if not isinstance(signtool, (list, tuple)):
        signtool = [signtool]
    cmd = signtool + ["-v", "-n", nonce, "-t", token, "-c", cert]
    for s in get_suitable_signing_servers(context.signing_servers, cert_type, signing_formats):
        cmd.extend(["-H", s.server])
    for f in signing_formats:
        cmd.extend(["-f", f])
    cmd.extend(["-o", to, from_])
    log.info("Running %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=STDOUT)
    log.info("COMMAND OUTPUT: ")
    await log_output(proc.stdout)
    exitcode = await proc.wait()
    log.info("exitcode {}".format(exitcode))
    abs_to = os.path.join(work_dir, to)
    log.info("SHA512SUM: %s SIGNED_FILE: %s",
             get_hash(abs_to, "sha512"), to)
    log.info("SHA1SUM: %s SIGNED_FILE: %s",
             get_hash(abs_to, "sha1"), to)
    log.info("Finished signing")


def get_suitable_signing_servers(signing_servers, cert_type, signing_formats):
    return [s for s in signing_servers[cert_type] if set(signing_formats) & set(s.formats)]


async def download_files(context):
    payload = context.task["payload"]
    file_urls = payload["unsignedArtifacts"]
    work_dir = context.config['work_dir']

    tasks = []
    files = []
    # TODO we need to make sure that these urls are all valid, e.g. artifacts
    # of parent tasks in the graph
    for file_url in file_urls:
        parts = urlparse(file_url)
        filename = parts.path.split('/')[-1]
        abs_file_path = os.path.join(work_dir, filename)
        files.append(filename)
        tasks.append(
            asyncio.ensure_future(
                retry_async(download_file, args=(context, file_url, abs_file_path))
            )
        )

    await raise_future_exceptions(tasks)
    tasks = []
    return files.keys()
