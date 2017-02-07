import hashlib
from copy import deepcopy
import json
import logging
import os
import pprint

import arrow
import jinja2
import yaml

from beetmoverscript.constants import (HASH_BLOCK_SIZE, STAGE_PLATFORM_MAP,
                                       TEMPLATE_KEY_PLATFORMS)

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


def get_size(filepath):
    """Function to return the size of a file based on filename"""
    return os.path.getsize(filepath)


def load_json(path):
    """Function to load a json from a file"""
    with open(path, "r") as fh:
        return json.load(fh)


def write_json(path, contents):
    """Function to dump a json content to a file"""
    with open(path, "w") as fh:
        json.dump(contents, fh, indent=4)


def write_file(path, contents):
    """Function to dump some string contents to a file"""
    with open(path, "w") as fh:
        fh.write(contents)


def generate_beetmover_template_args(task, release_props):
    tmpl_key_platform = TEMPLATE_KEY_PLATFORMS[release_props["stage_platform"]]

    template_args = {
        # payload['upload_date'] is a timestamp defined by params['pushdate']
        # in mach taskgraph0
        "upload_date": arrow.get(task['payload']['upload_date']).format('YYYY/MM/YYYY-MM-DD-HH-mm-ss'),
        "version": release_props["appVersion"],
        "branch": release_props["branch"],
        "product": release_props["appName"],
        "stage_platform": release_props["stage_platform"],
        "platform": release_props["platform"],
    }

    if 'locale' in task["payload"]:
        template_args["locale"] = task["payload"]["locale"]
        template_args["template_key"] = "%s_nightly_repacks" % release_props["appName"].lower()
    else:
        template_args["template_key"] = "%s_nightly" % tmpl_key_platform

    return template_args


def generate_beetmover_manifest(script_config, task, release_props):
    """
    generates and outputs a manifest that maps expected Taskcluster artifact names
    to release deliverable names
    """
    template_args = generate_beetmover_template_args(task, release_props)
    template_path = script_config['template_files'][template_args["template_key"]]

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


def update_props(props, platform_mapping):
    """Function to alter the `stage_platform` field from balrog_props to their
    corresponding correct values for certain platforms. Please note that for
    l10n jobs the `stage_platform` field is in fact called `platform` hence
    the defaulting below."""
    props = deepcopy(props)
    # en-US jobs have the platform set in the `stage_platform` field while
    # l10n jobs have it set under `platform`. This is merely an uniformization
    # under the `stage_platform` field that is needed later on in the templates
    stage_platform = props.get("stage_platform", props.get("platform"))
    props["stage_platform"] = stage_platform
    # for some products/platforms this mapping is not needed, hence the default
    props["platform"] = platform_mapping.get(stage_platform,
                                             stage_platform)
    return props


def get_release_props(initial_release_props_file, platform_mapping=STAGE_PLATFORM_MAP):
    """determined via parsing the Nightly build job's balrog_props.json and
    expanded the properties with props beetmover knows about."""
    props = load_json(initial_release_props_file)['properties']
    return update_props(props, platform_mapping)


def alter_unpretty_contents(context, blobs, mappings):
    """Function to alter any unpretty-name contents from a file specified in script
    configs."""
    for blob in blobs:
        for locale in context.artifacts_to_beetmove:
            source = context.artifacts_to_beetmove[locale].get(blob)
            if not source:
                continue

            contents = load_json(source)
            pretty_contents = deepcopy(contents)
            for package, tests in contents.items():
                new_tests = []
                for artifact in tests:
                    pretty_dict = mappings['mapping'][locale].get(artifact)
                    if pretty_dict:
                        new_tests.append(os.path.basename(pretty_dict['s3_key']))
                    else:
                        new_tests.append(artifact)
                if new_tests != tests:
                    pretty_contents[package] = new_tests

            if pretty_contents != contents:
                write_json(source, pretty_contents)
