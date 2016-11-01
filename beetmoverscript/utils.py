import hashlib
import json
import logging
import os
import pprint

import arrow
import jinja2
import yaml

log = logging.getLogger(__name__)


def get_hash(filepath, hash_type="sha512"):
    digest = hashlib.new(hash_type)
    with open(filepath, "rb") as fobj:
        while True:
            chunk = fobj.read(1024*1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def infer_template_args(context):
    props = context.properties
    tmpl_key_option = "signed" if context.task["payload"]["update_manifest"] is True else "unsigned"

    return {
        "version": props["appVersion"],
        "branch": props["branch"],
        "product": props["appName"],
        "stage_platform": props["stage_platform"],
        "template_key": "%s_nightly_%s" % (
            props["appName"].lower(),
            tmpl_key_option
        )
    }


def generate_candidates_manifest(context):
    """
    generates and outputs a manifest that maps expected Taskcluster artifact names
    to release deliverable names
    """
    payload = context.task['payload']

    template_args = {
        "taskid_to_beetmove": payload["taskid_to_beetmove"],
        "taskid_of_manifest": payload["taskid_of_manifest"],
        "update_manifest": payload["update_manifest"],
        # payload['upload_date'] is a timestamp defined by params['pushdate']
        # in mach taskgraph0
        "upload_date": arrow.get(payload['upload_date']).format('YYYY/MM/YYYY-MM-DD-HH-mm-ss')
    }

    template_args.update(infer_template_args(context))
    template_path = context.config['template_files'][template_args["template_key"]]

    log.info('generating manifest from: {}'.format(template_path))
    log.info(os.path.abspath(template_path))

    template_dir, template_name = os.path.split(os.path.abspath(template_path))
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                                   undefined=jinja2.StrictUndefined)
    template = jinja_env.get_template(template_name)
    manifest = yaml.safe_load(template.render(**template_args))

    log.info("manifest generated:")
    log.info(pprint.pformat(manifest))

    return manifest
