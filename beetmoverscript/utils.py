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


def generate_candidates_manifest(context):
    """
    generates and outputs a manifest that maps expected Taskcluster artifact names
    to release deliverable names
    """
    payload = context.task['payload']
    template_args = {
        "version": payload['version'],
        # payload['upload_date'] is a timestamp defined by params['pushdate'] in mach taskgraph
        "upload_date": arrow.get(payload['upload_date']).format('YYYY/MM/YYYY-MM-DD-HH-mm-ss'),
        "taskid_to_beetmove": payload["taskid_to_beetmove"]
    }
    template_path = context.config['template_files'][payload['template_key']]
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
