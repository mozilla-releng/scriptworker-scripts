import os
import random
import tempfile
import urlparse
import logging
import json

import sh
import requests

import arrow
import taskcluster

from signingscript.task import task_cert_type, \
    task_signing_formats
from signingscript.exceptions import TaskVerificationError, \
    ChecksumMismatchError, SigningServerError
from signingscript.utils import get_hash, get_detached_signatures

log = logging.getLogger(__name__)


def process_message(context, body, message):
    # move this to async_main ?
    task_id = None
    run_id = None
    work_dir = tempfile.mkdtemp()
    task = {}
    try:
        # validate_task(task)
        sign(task_id, run_id, task, work_dir)
        # copy to artifact_dir
    except taskcluster.exceptions.TaskclusterRestFailure as e:
        log.exception("TC REST failure, %s", e.status_code)
        if e.status_code == 409:
            log.debug("Task already claimed, acking...")
        else:
            raise
    except (TaskVerificationError, ):
        log.exception("Cannot verify task, %s", body)
        context.temp_queue.reportException(
            task_id, run_id, {"reason": "malformed-payload"})
    except Exception:
        log.exception("Error processing %s", body)


def download_and_sign_file(context, task_id, run_id, url, checksum, cert_type,
                           signing_formats, work_dir):
    # TODO: better parsing
    filename = urlparse.urlsplit(url).path.split("/")[-1]
    abs_filename = os.path.join(work_dir, filename)
    log.debug("Downloading %s", url)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    with open(abs_filename, 'wb') as fd:
        for chunk in r.iter_content(4096):
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
    sign_file(work_dir, filename, cert_type, signing_formats)
    create_artifact(task_id, run_id, "public/env/%s" % filename,
                    abs_filename)
    detached_signatures = []
    for s_type, s_ext, s_mime in get_detached_signatures(signing_formats):
        d_filename = "{filename}{ext}".format(filename=filename,
                                              ext=s_ext)
        d_abs_filename = os.path.join(work_dir, d_filename)
        create_artifact(task_id, run_id, "public/env/%s" % d_filename,
                        d_abs_filename, content_type=s_mime)
        detached_signatures.append((s_type, d_filename))
    return abs_filename, detached_signatures


def create_artifact(context, task_id, run_id, dest, abs_filename,
                    content_type="application/octet-stream"):
    log.debug("Uploading artifact %s (t: %s, r: %s) from %s (%s)", dest,
              task_id, run_id, abs_filename, content_type)
    # TODO: better expires
    res = context.temp_queue.createArtifact(
        task_id, run_id, dest,
        {
            "storageType": "s3",
            "contentType": content_type,
            "expires": arrow.now().replace(weeks=2).isoformat()
        }
    )
    log.debug("Got %s", res)
    put_url = res["putUrl"]
    log.debug("Uploading to %s", put_url)
    taskcluster.utils.putFile(abs_filename, put_url, content_type)
    log.debug("Done")


# @redo.retriable(attempts=10, sleeptime=5, max_sleeptime=30)
def get_token(all_signing_servers, output_file, cert_type, signing_formats, my_ip):
    token = None
    data = {"slave_ip": my_ip, "duration": 5 * 60}
    signing_servers = get_suitable_signing_servers(all_signing_servers, cert_type,
                                                   signing_formats)
    random.shuffle(signing_servers)
    for s in signing_servers:
        log.debug("getting token from %s", s.server)
        # TODO: Figure out how to deal with certs not matching hostname,
        #  error: https://gist.github.com/rail/cbacf2d297decb68affa
        r = requests.post("https://{}/token".format(s.server), data=data,
                          auth=(s.user, s.password), timeout=60,
                          verify=False)
        r.raise_for_status()
        if r.content:
            token = r.content
            log.debug("Got token")
            break
    if not token:
        raise SigningServerError("Cannot retrieve signing token")
    with open(output_file, "wb") as f:
        f.write(token)


def sign_file(context, work_dir, from_, cert_type, signing_formats, cert, to=None):
    if to is None:
        to = from_
    token = os.path.join(work_dir, "token")
    nonce = os.path.join(work_dir, "nonce")
    get_token(token, cert_type, signing_formats)
    # TODO path to tools
    signtool = os.path.join("tools_checkout", "release/signing/signtool.py")
    cmd = [signtool, "-n", nonce, "-t", token, "-c", cert]
    for s in get_suitable_signing_servers(cert_type, signing_formats):
        cmd.extend(["-H", s.server])
    for f in signing_formats:
        cmd.extend(["-f", f])
    cmd.extend(["-o", to, from_])
    log.debug("Running python %s", " ".join(cmd))
    out = sh.python(*cmd, _err_to_out=True, _cwd=work_dir)
    log.debug("COMMAND OUTPUT: %s", out)
    abs_to = os.path.join(work_dir, to)
    log.info("SHA512SUM: %s SIGNED_FILE: %s",
             get_hash(abs_to, "sha512"), to)
    log.info("SHA1SUM: %s SIGNED_FILE: %s",
             get_hash(abs_to, "sha1"), to)
    log.debug("Finished signing")


def get_suitable_signing_servers(signing_servers, cert_type, signing_formats):
    return [s for s in signing_servers[cert_type] if
            set(signing_formats) & set(s.formats)]


#    @redo.retriable(attempts=10, sleeptime=5, max_sleeptime=30)
def get_manifest(url):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def sign(context, task_id, run_id):
    payload = context.task["payload"]
    manifest_url = payload["signingManifest"]
    work_dir = context.config['work_dir']
    signing_manifest = get_manifest(manifest_url)
    # TODO: better way to extract filename
    url_prefix = "/".join(manifest_url.split("/")[:-1])
    cert_type = task_cert_type(context.task)
    signing_formats = task_signing_formats(context.task)
    for e in signing_manifest:
        # Fallback to "mar" if "file_to_sign" is not specified
        file_to_sign = e.get("file_to_sign", e.get("mar"))
        file_url = "{}/{}".format(url_prefix, file_to_sign)
        abs_filename, detached_signatures = download_and_sign_file(
            task_id, run_id, file_url, e["hash"], cert_type,
            signing_formats, work_dir)
        # Update manifest data with new values
        e["hash"] = get_hash(abs_filename)
        e["size"] = os.path.getsize(abs_filename)
        e["detached_signatures"] = {}
        for sig_type, sig_filename in detached_signatures:
            e["detached_signatures"][sig_type] = sig_filename
    manifest_file = os.path.join(work_dir, "manifest.json")
    with open(manifest_file, "wb") as f:
        json.dump(signing_manifest, f, indent=2, sort_keys=True)
    log.debug("Uploading manifest for t: %s, r: %s", task_id, run_id)
    create_artifact(task_id, run_id, "public/env/manifest.json",
                    manifest_file, "application/json")
