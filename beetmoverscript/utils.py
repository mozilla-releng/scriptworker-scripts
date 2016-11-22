import hashlib
from copy import deepcopy
import json
import logging
import os
import pprint

import arrow
import jinja2
import yaml

from beetmoverscript.constants import (HASH_BLOCK_SIZE, MANIFEST_L10N_URL_TMPL,
                                       MANIFEST_URL_TMPL)

log = logging.getLogger(__name__)


def get_hash(filepath, hash_type="sha512"):
    """Function to return the digest hash of a file based on filename and
    algorithm"""
    digest = hashlib.new(hash_type)
    with open(filepath, "rb") as fobj:
        while True:
            chunk = fobj.read(HASH_BLOCK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def write_json(path, contents):
    with open(path, "w") as fh:
        json.dump(contents, fh)


def get_manifest_url(payload):
    """Function to toggle between en-US and l10n balrog_props manifest url"""
    taskid_of_manifest = payload['taskid_of_manifest']
    if 'locale' in payload:
        return MANIFEST_L10N_URL_TMPL % (taskid_of_manifest, payload['locale'])

    return MANIFEST_URL_TMPL % taskid_of_manifest


def infer_template_args(context):
    props = context.properties
    # Bug 1313154 - in order to make beetmoverscript accommodate the nightly
    # graph, task payload was tweaked to encompass `update_manifest` boolean
    # flag. The builds with unsigned artifacts will always have the flag set to
    # False while the builds with signed artifacts will have the opposite,
    # marking the need to update the manifest to be passed down to balrogworker
    tmpl_key_option = "signed" if context.task["payload"]["update_manifest"] is True else "unsigned"
    _args = {
        "version": props["appVersion"],
        "branch": props["branch"],
        "product": props["appName"],
        "stage_platform": props["stage_platform"],
        "platform": props["platform"],
        "template_key": "%s_nightly_%s" % (
            props["appName"].lower(),
            tmpl_key_option
        )
    }

    if 'locale' in context.task["payload"]:
        _args["locale"] = context.task["payload"]["locale"]
        # overwrite the `template_key` with the repacks string version
        _args["template_key"] = "%s_nightly_repacks_%s" % (
            props["appName"].lower(),
            tmpl_key_option
        )

    return _args


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


def update_props(context_props, platform_mapping):
    """Function to alter the `stage_platform` field from balrog_props to their
    corresponding correct values for certain platforms. Please note that for
    l10n jobs the `stage_platform` field is in fact called `platform` hence
    the defaulting below."""
    props = deepcopy(context_props)
    # en-US jobs have the platform set in the `stage_platform` field while
    # l10n jobs have it set under `platform`. This is merely an uniformization
    # under the `stage_platform` field that is needed later on in the templates
    stage_platform = props.get("stage_platform", props.get("platform"))
    props["stage_platform"] = stage_platform
    # for some products/platforms this mapping is not needed, hence the default
    props["platform"] = platform_mapping.get(stage_platform,
                                             stage_platform)
    return props
