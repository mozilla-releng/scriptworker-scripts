import json
import os
import logging
import pprint

import arrow
import jinja2
import yaml

log = logging.getLogger(__name__)


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def infer_template_args(context):
    props = context.properties
    # Bug 1313154 - in order to make beetmoverscript accommodate the nightly
    # graph, task payload was tweaked to encompass `update_manifest` boolean
    # flag. The builds with unsigned artifacts will always have the flag set to
    # False while the builds with signed artifacts will have the opposite,
    # marking the need to update the manifest to be passed down to balrogworker
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
