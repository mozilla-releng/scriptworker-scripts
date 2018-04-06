import arrow
from copy import deepcopy
import hashlib
import jinja2
import json
import logging
import os
import pprint
import re
import yaml

from beetmoverscript.constants import (
    HASH_BLOCK_SIZE,
    RELEASE_ACTIONS, PROMOTION_ACTIONS, PRODUCT_TO_PATH,
    NORMALIZED_FILENAME_PLATFORMS,
)

log = logging.getLogger(__name__)


JINJA_ENV = jinja2.Environment(loader=jinja2.PackageLoader("beetmoverscript"),
                               undefined=jinja2.StrictUndefined)


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


def is_release_action(action):
    """Function to return boolean if we're publishing a release as opposed to a
    nightly release or something else. Does that by checking the action type.
    """
    return action in RELEASE_ACTIONS


def is_promotion_action(action):
    """Function to return boolean if we're promoting a release as opposed to a
    nightly or something else. Does that by checking the action type.
    """
    return action in PROMOTION_ACTIONS


def get_product_name(appName, platform):
    if "devedition" in platform:
        # XXX: this check is helps reuse this function in both
        # returning the proper templates file but also for the release name in
        # Balrog manifest that beetmover is uploading upon successful run
        if appName[0].isupper():
            return "Devedition"
        else:
            return "devedition"
    return appName


def generate_beetmover_template_args(context):
    task = context.task
    release_props = context.release_props

    tmpl_args = {
        # payload['upload_date'] is a timestamp defined by params['pushdate']
        # in mach taskgraph
        "upload_date": arrow.get(task['payload']['upload_date']).format('YYYY/MM/YYYY-MM-DD-HH-mm-ss'),
        "version": release_props["appVersion"],
        "branch": release_props["branch"],
        "product": release_props["appName"],
        "stage_platform": release_props["stage_platform"],
        "platform": release_props["platform"],
        "buildid": release_props["buildid"],
        "partials": get_partials_props(task),
        "filename_platform": NORMALIZED_FILENAME_PLATFORMS.get(release_props["stage_platform"],
                                                               release_props["stage_platform"]),
    }

    if is_promotion_action(context.action) or is_release_action(context.action):
        tmpl_args["build_number"] = task['payload']['build_number']
        tmpl_args["version"] = task['payload']['version']

    # e.g. action = 'push-to-candidates' or 'push-to-nightly'
    tmpl_bucket = context.action.split('-')[-1]

    product_name = get_product_name(release_props["appName"].lower(), release_props["stage_platform"])
    if 'locale' in task["payload"]:
        tmpl_args["locale"] = task["payload"]["locale"]
        tmpl_args["template_key"] = "%s_%s_repacks" % (product_name, tmpl_bucket)
    else:
        tmpl_args["template_key"] = "%s_%s" % (product_name, tmpl_bucket)

    return tmpl_args


def generate_beetmover_manifest(context):
    """
    generates and outputs a manifest that maps expected Taskcluster artifact names
    to release deliverable names
    """
    tmpl_args = generate_beetmover_template_args(context)

    tmpl_name = '{}.yml'.format(tmpl_args["template_key"])
    jinja_env = JINJA_ENV
    tmpl = jinja_env.get_template(tmpl_name)

    log.info('generating manifest from: {}'.format(tmpl.filename))

    manifest = yaml.safe_load(tmpl.render(**tmpl_args))

    log.info("manifest generated:")
    log.info(pprint.pformat(manifest))

    return manifest


def get_partials_props(task):
    """Examine contents of task.json (stored in context.task) and extract
    partials mapping data from the 'extra' field"""
    partials = task.get('extra', {}).get('partials', {})
    return {p['artifact_name']: p for p in partials}


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
                        new_tests.append(pretty_dict['s3_key'])
                    else:
                        new_tests.append(artifact)
                if new_tests != tests:
                    pretty_contents[package] = new_tests

            if pretty_contents != contents:
                write_json(source, pretty_contents)


def get_candidates_prefix(product, version, build_number):
    return "{}candidates/{}-candidates/build{}/".format(
        PRODUCT_TO_PATH[product], version, str(build_number)
    )


def get_releases_prefix(product, version):
    return "{}releases/{}/".format(PRODUCT_TO_PATH[product], version)


def matches_exclude(keyname, excludes):
    for exclude in excludes:
        if re.search(exclude, keyname):
            return True
    return False


def get_creds(context):
    return context.config['bucket_config'][context.bucket]['credentials']


def get_bucket_name(context, product):
    return context.config['bucket_config'][context.bucket]['buckets'][product]
