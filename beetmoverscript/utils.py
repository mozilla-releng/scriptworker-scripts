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

from mozilla_version.maven import MavenVersion
from mozilla_version.gecko import FirefoxVersion
from scriptworker.exceptions import TaskVerificationError

from beetmoverscript.constants import (
    HASH_BLOCK_SIZE,
    RELEASE_ACTIONS, PROMOTION_ACTIONS, MAVEN_ACTIONS, PRODUCT_TO_PATH,
    NORMALIZED_FILENAME_PLATFORMS, PARTNER_REPACK_ACTIONS,
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


def is_partner_action(action):
    """Function to return boolean if we're promoting a release as opposed to a
    nightly or something else. Does that by checking the action type.
    """
    return action in PARTNER_REPACK_ACTIONS


def is_maven_action(action):
    """Function to return boolean if the task intends to upload onto maven.
    Geckoview uploads to maven, for instance. Does that by checking the action type.
    """
    return action in MAVEN_ACTIONS


def is_partner_private_task(context):
    """Function to return boolean if we're considering a public partner task.
    Does that by checking the action type and presence of a flag in payload
    """
    return (is_partner_action(context.action) and 'partner' in context.bucket)


def is_partner_public_task(context):
    """Function to return boolean if we're considering a private partner task.
    Does that by checking the action type and absence of a flag in payload
    """
    return (is_partner_action(context.action) and 'partner' not in context.bucket)


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

    if is_maven_action(context.action):
        return _generate_beetmover_template_args_maven(task, release_props)

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

    if (is_promotion_action(context.action) or
        is_release_action(context.action) or
            is_partner_action(context.action)):
        tmpl_args["build_number"] = task['payload']['build_number']
        tmpl_args["version"] = task['payload']['version']

    # e.g. action = 'push-to-candidates' or 'push-to-nightly'
    tmpl_bucket = context.action.split('-')[-1]

    locales_in_upstream_artifacts = [
        upstream_artifact['locale']
        for upstream_artifact in task['payload']['upstreamArtifacts']
        if 'locale' in upstream_artifact
    ]
    uniques_locales_in_upstream_artifacts = sorted(list(set(locales_in_upstream_artifacts)))

    if 'locale' in task['payload'] and uniques_locales_in_upstream_artifacts:
        _check_locale_consistency(task['payload']['locale'], uniques_locales_in_upstream_artifacts)
        tmpl_args['locales'] = uniques_locales_in_upstream_artifacts
    elif uniques_locales_in_upstream_artifacts:
        tmpl_args['locales'] = uniques_locales_in_upstream_artifacts
    elif 'locale' in task['payload']:
        tmpl_args['locales'] = [task['payload']['locale']]

    product_name = get_product_name(
        release_props["appName"].lower(), release_props["stage_platform"])
    if tmpl_args.get('locales') and (
            # we only apply the repacks template if not english or android "multi" locale
            set(tmpl_args.get('locales')).isdisjoint({'en-US', 'multi'})):
        tmpl_args["template_key"] = "%s_%s_repacks" % (product_name, tmpl_bucket)
    else:
        tmpl_args["template_key"] = "%s_%s" % (product_name, tmpl_bucket)

    return tmpl_args


def _generate_beetmover_template_args_maven(task, release_props):
    tmpl_args = {
        'artifact_id': task['payload']['artifact_id'],
        'template_key': 'maven_{}'.format(release_props['appName']),
    }

    # FIXME: this is a temporarily solution while we sanitize the payload
    # under https://github.com/mozilla-releng/beetmoverscript/issues/196
    if 'SNAPSHOT' in task['payload']['version']:
        payload_version = MavenVersion.parse(task['payload']['version'])
    else:
        payload_version = FirefoxVersion.parse(task['payload']['version'])
    # Change version number to major.minor.buildId because that's what the build task produces
    version = [payload_version.major_number,
               payload_version.minor_number,
               release_props.get('buildid', payload_version.patch_number)]
    if any(number is None for number in version):
        raise TaskVerificationError('At least one digit is undefined. Got: {}'.format(version))
    tmpl_args['version'] = '.'.join(str(n) for n in version)

    if isinstance(payload_version, MavenVersion) and payload_version.is_snapshot:
        tmpl_args['snapshot_version'] = payload_version
        tmpl_args['date_timestamp'] = "{{date_timestamp}}"
        tmpl_args['clock_timestamp'] = "{{clock_timestamp}}"
        tmpl_args['build_number'] = "{{build_number}}"

    return tmpl_args


def _check_locale_consistency(locale_in_payload, uniques_locales_in_upstream_artifacts):
    if len(uniques_locales_in_upstream_artifacts) > 1:
        raise TaskVerificationError(
            '`task.payload.locale` is defined ("{}") but too many locales set in \
`task.payload.upstreamArtifacts` ({})'.format(locale_in_payload, uniques_locales_in_upstream_artifacts)
        )
    elif len(uniques_locales_in_upstream_artifacts) == 1:
        locale_in_upstream_artifacts = uniques_locales_in_upstream_artifacts[0]
        if locale_in_payload != locale_in_upstream_artifacts:
            raise TaskVerificationError(
                '`task.payload.locale` ("{}") does not match the one set in \
`task.payload.upstreamArtifacts` ("{}")'.format(locale_in_payload, locale_in_upstream_artifacts)
            )


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


def get_bucket_url_prefix(context):
    return context.config['bucket_config'][context.bucket]['url_prefix']


def validated_task_id(task_id):
    """Validate the format of a taskcluster taskId."""
    pattern = r'^[A-Za-z0-9_-]{8}[Q-T][A-Za-z0-9_-][CGKOSWaeimquy26-][A-Za-z0-9_-]{10}[AQgw]$'
    if re.fullmatch(pattern, task_id):
        return task_id
    raise ValueError("No valid taskId found.")


def extract_file_config_from_artifact_map(artifact_map, path, task_id, locale):
    """Return matching artifact map config."""
    for entry in artifact_map:
        if entry['taskId'] != task_id or entry['locale'] != locale:
            continue
        if not entry['paths'].get(path):
            continue
        return entry['paths'][path]
    raise TaskVerificationError('No artifact map entry for {}/{} {}'.format(task_id, locale, path))
