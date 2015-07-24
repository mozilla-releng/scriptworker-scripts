import os
import random
import shutil
import tempfile
import urlparse
import logging
import json
import re

import arrow
from jsonschema import ValidationError
from kombu import Exchange, Queue
from kombu.mixins import ConsumerMixin
import redo
import requests
import sh
import taskcluster

from signingworker.task import validate_task, task_cert_type, \
    task_signing_formats
from signingworker.exceptions import TaskVerificationError, \
    ChecksumMismatchError, SigningServerError
from signingworker.utils import get_hash, load_signing_server_config, \
    get_detached_signatures

log = logging.getLogger(__name__)


class SigningConsumer(ConsumerMixin):

    def __init__(self, connection, exchange, queue_name, worker_type,
                 taskcluster_config, signing_server_config, tools_checkout,
                 my_ip, worker_id):
        self.connection = connection
        self.exchange = Exchange(exchange, type='topic', passive=True)
        self.queue_name = queue_name
        self.worker_type = worker_type
        self.routing_key = "*.*.*.*.*.*.{}.#".format(self.worker_type)
        self.tc_queue = taskcluster.Queue(taskcluster_config)
        self.signing_servers = load_signing_server_config(
            signing_server_config)
        self.tools_checkout = tools_checkout
        self.cert = os.path.join(self.tools_checkout,
                                 "release/signing/host.cert")
        self.my_ip = my_ip
        # make sure we meet TC requirements
        self.worker_id = re.sub(r"[^a-zA-Z0-9-_]", "_", worker_id)[:22]

    def get_consumers(self, consumer_cls, channel):
        queue = Queue(name=self.queue_name, exchange=self.exchange,
                      routing_key=self.routing_key, durable=True,
                      exclusive=False, auto_delete=False)
        return [consumer_cls(queues=[queue], callbacks=[self.process_message])]

    def process_message(self, body, message):
        task_id = None
        run_id = None
        work_dir = tempfile.mkdtemp()
        try:
            task_id = body["status"]["taskId"]
            run_id = body["status"]["runs"][-1]["runId"]
            log.debug("Claiming task %s, run %s", task_id, run_id)
            self.tc_queue.claimTask(
                task_id, run_id,
                {"workerGroup": self.worker_type, "workerId": self.worker_id}
            )
            task = self.tc_queue.task(task_id)
            task_graph_id = task["taskGroupId"]
            validate_task(task)
            self.sign(task_id, run_id, task, work_dir)
            log.debug("Completing: %s, r: %s", task_id, run_id)
            self.tc_queue.reportCompleted(task_id, run_id)
            log.debug("Complete: %s, r: %s, tg: %s", task_id, run_id,
                      task_graph_id)
        except taskcluster.exceptions.TaskclusterRestFailure as e:
            log.exception("TC REST failure, %s", e.status_code)
            if e.status_code == 409:
                log.debug("Task already claimed, acking...")
            else:
                raise
        except (TaskVerificationError, ValidationError):
            log.exception("Cannot verify task, %s", body)
            self.tc_queue.reportException(
                task_id, run_id, {"reason": "malformed-payload"})
        except Exception:
            log.exception("Error processing %s", body)

        message.ack()
        shutil.rmtree(work_dir)

    @redo.retriable(attempts=10, sleeptime=5, max_sleeptime=30)
    def get_manifest(self, url):
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def sign(self, task_id, run_id, task, work_dir):
        payload = task["payload"]
        manifest_url = payload["signingManifest"]
        signing_manifest = self.get_manifest(manifest_url)
        # TODO: better way to extract filename
        url_prefix = "/".join(manifest_url.split("/")[:-1])
        cert_type = task_cert_type(task)
        signing_formats = task_signing_formats(task)
        for e in signing_manifest:
            # TODO: "mar" is too specific, change the manifest
            file_url = "{}/{}".format(url_prefix, e["mar"])
            abs_filename, detached_signatures = self.download_and_sign_file(
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
        self.create_artifact(task_id, run_id, "public/env/manifest.json",
                             manifest_file, "application/json")

    def download_and_sign_file(self, task_id, run_id, url, checksum, cert_type,
                               signing_formats, work_dir):
        # TODO: better parsing
        filename = urlparse.urlsplit(url).path.split("/")[-1]
        abs_filename = os.path.join(work_dir, filename)
        log.debug("Downloading %s", url)
        r = requests.get(url)
        r.raise_for_status()
        with open(abs_filename, 'wb') as fd:
            for chunk in r.iter_content(4096):
                fd.write(chunk)
        log.debug("Done")
        got_checksum = get_hash(abs_filename)
        if not got_checksum == checksum:
            log.debug("Checksum mismatch, cleaning up...")
            raise ChecksumMismatchError("Expected {}, got {} for {}".format(
                checksum, got_checksum, url
            ))
        log.debug("Signing %s", filename)
        self.sign_file(work_dir, filename, cert_type, signing_formats)
        self.create_artifact(task_id, run_id, "public/env/%s" % filename,
                             abs_filename)
        detached_signatures = []
        for s_type, s_ext, s_mime in get_detached_signatures(signing_formats):
            d_filename = "{filename}{ext}".format(filename=filename,
                                                  ext=s_ext)
            d_abs_filename = os.path.join(work_dir, d_filename)
            self.create_artifact(task_id, run_id, "public/env/%s" % d_filename,
                                 d_abs_filename, content_type=s_mime)
            detached_signatures.append((s_type, d_filename))
        return abs_filename, detached_signatures

    def create_artifact(self, task_id, run_id, dest, abs_filename,
                        content_type="application/octet-stream"):
        log.debug("Uploading artifact %s (t: %s, r: %s) from %s (%s)", dest,
                  task_id, run_id, abs_filename, content_type)
        # TODO: better expires
        res = self.tc_queue.createArtifact(
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

    @redo.retriable(attempts=10, sleeptime=5, max_sleeptime=30)
    def get_token(self, output_file, cert_type, signing_formats):
        token = None
        data = {"slave_ip": self.my_ip, "duration": 5 * 60}
        signing_servers = self.get_suitable_signing_servers(cert_type,
                                                            signing_formats)
        random.shuffle(signing_servers)
        for s in signing_servers:
            log.debug("getting token from %s", s.server)
            # TODO: Figure out how to deal with certs not matching hostname,
            #  error: https://gist.github.com/rail/cbacf2d297decb68affa
            r = requests.post("https://{}/token".format(s.server), data=data,
                              auth=(s.user, s.password),
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

    def sign_file(self, work_dir, from_, cert_type, signing_formats, to=None):
        if to is None:
            to = from_
        token = os.path.join(work_dir, "token")
        nonce = os.path.join(work_dir, "nonce")
        self.get_token(token, cert_type, signing_formats)
        signtool = os.path.join(self.tools_checkout,
                                "release/signing/signtool.py")
        cmd = [signtool, "-n", nonce, "-t", token, "-c", self.cert]
        for s in self.get_suitable_signing_servers(cert_type, signing_formats):
            cmd.extend(["-H", s.server])
        for f in signing_formats:
            cmd.extend(["-f", f])
        cmd.extend(["-o", to, from_])
        log.debug("Running python %s", " ".join(cmd))
        sh.python(*cmd, _err_to_out=True, _cwd=work_dir)
        log.debug("Finished signing")

    def get_suitable_signing_servers(self, cert_type, signing_formats):
        return [s for s in self.signing_servers[cert_type] if
                set(signing_formats) & set(s.formats)]
