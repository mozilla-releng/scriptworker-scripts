import arrow
import logging
import os
import re
import urllib.parse

from copy import deepcopy
from scriptworker import client

from beetmoverscript import utils, script

from beetmoverscript.constants import (
    STAGE_PLATFORM_MAP,
    RESTRICTED_BUCKET_PATHS,
    CHECKSUMS_CUSTOM_FILE_NAMING
)
from scriptworker import artifacts as scriptworker_artifacts
from scriptworker.exceptions import ScriptWorkerTaskException

log = logging.getLogger(__name__)


def validate_task_schema(context):
    """Perform a schema validation check against taks definition"""
    action = get_task_action(context.task, context.config)
    schema_key = 'release_schema_file' if utils.is_release_action(action) else 'schema_file'
    client.validate_task_schema(context, schema_key=schema_key)


def get_task_bucket(task, script_config):
    """Extract task bucket from scopes"""
    buckets = [s.split(':')[-1] for s in task["scopes"] if
               s.startswith(script_config["taskcluster_scope_prefix"] + "bucket:")]
    log.info("Buckets: %s", buckets)
    messages = []
    if len(buckets) != 1:
        messages.append("Only one bucket can be used")

    bucket = buckets[0]
    if re.search('^[0-9A-Za-z_-]+$', bucket) is None:
        messages.append("Bucket {} is malformed".format(bucket))

    if bucket not in script_config['bucket_config']:
        messages.append("Invalid bucket scope")

    if messages:
        raise ScriptWorkerTaskException("\n".join(messages))

    return bucket


def get_task_action(task, script_config):
    """Extract last part of beetmover action scope"""
    actions = [s.split(":")[-1] for s in task["scopes"] if
               s.startswith(script_config["taskcluster_scope_prefix"] + "action:")]

    log.info("Action types: %s", actions)
    messages = []
    if len(actions) != 1:
        messages.append("Only one action type can be used")

    action = actions[0]
    if action not in script.action_map:
        messages.append("Invalid action scope")

    if messages:
        raise ScriptWorkerTaskException('\n'.join(messages))

    return action


def validate_bucket_paths(bucket, s3_bucket_path):
    """Double check the S3 bucket path is valid for the given bucket"""
    try:
        paths = RESTRICTED_BUCKET_PATHS[bucket]
    except KeyError:
        raise ScriptWorkerTaskException('Unknown bucket "{}"'.format(s3_bucket_path))
    if not any([s3_bucket_path.startswith(p) for p in paths]):
        raise ScriptWorkerTaskException("Forbidden S3 {} destination".format(s3_bucket_path))


def generate_checksums_manifest(context):
    checksums_dict = context.checksums
    content = list()
    for artifact, values in sorted(checksums_dict.items()):
        for algo in context.config['checksums_digests']:
            content.append("{} {} {} {}".format(
                values[algo],
                algo,
                values['size'],
                artifact
            ))

    return '\n'.join(content)


def is_custom_checksums_task(context):
    return CHECKSUMS_CUSTOM_FILE_NAMING.get(context.task['tags']['kind'], '')


def add_checksums_to_artifacts(context):
    name = is_custom_checksums_task(context)
    filename = 'public/target{}.checksums'.format(name)

    abs_file_path = os.path.join(context.config['artifact_dir'],
                                 filename)
    manifest = generate_checksums_manifest(context)
    utils.write_file(abs_file_path, manifest)


def add_balrog_manifest_to_artifacts(context):
    abs_file_path = os.path.join(context.config['artifact_dir'],
                                 'public/manifest.json')
    utils.write_json(abs_file_path, context.balrog_manifest)


def get_upstream_artifacts(context, preserve_full_paths=False):
    artifacts = {}
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        locale = artifact_dict['locale']
        artifacts[locale] = artifacts.get(locale, {})
        for path in artifact_dict['paths']:
            abs_path = scriptworker_artifacts.get_and_check_single_upstream_artifact_full_path(
                context, artifact_dict['taskId'], path
            )
            if preserve_full_paths:
                artifacts[locale][path] = abs_path
            else:
                artifacts[locale][os.path.basename(abs_path)] = abs_path
    return artifacts


def get_upstream_artifacts_with_zip_extract_param(context):
    # XXX A dict comprehension isn't used because upstream_definition would be erased if the same
    # taskId is present twice in upstreamArtifacts
    upstream_artifacts_per_task_id = {}

    for artifact_definition in context.task['payload']['upstreamArtifacts']:
        task_id = artifact_definition['taskId']
        upstream_definitions = upstream_artifacts_per_task_id.get(task_id, [])

        new_upstream_definition = {
            'paths': [
                scriptworker_artifacts.get_and_check_single_upstream_artifact_full_path(context, task_id, path)
                for path in artifact_definition['paths']
            ],
            'zip_extract': artifact_definition.get('zipExtract', False),
        }

        upstream_definitions.append(new_upstream_definition)
        upstream_artifacts_per_task_id[task_id] = upstream_definitions

    return upstream_artifacts_per_task_id


def get_release_props(context, platform_mapping=STAGE_PLATFORM_MAP):
    """determined via parsing the Nightly build job's payload and
    expanded the properties with props beetmover knows about."""
    payload_properties = context.task.get('payload', {}).get('releaseProperties', None)

    if not payload_properties:
        raise ScriptWorkerTaskException(
            "could not determine release props file from task payload"
        )

    log.debug("Loading release_props from task's payload: {}".format(payload_properties))
    return update_props(context, payload_properties, platform_mapping)


def update_props(context, props, platform_mapping):
    """Function to alter slightly the `platform` value and to enrich context with
    `stage_platform` as we need both in the beetmover template manifests."""
    props = deepcopy(props)

    stage_platform = props.get('platform', '')
    # for some products/platforms this mapping is not needed, hence the default
    props["platform"] = platform_mapping.get(stage_platform, stage_platform)
    props["stage_platform"] = stage_platform
    return props


def get_updated_buildhub_artifact(path, installer_path, context, manifest, locale):
    """
    Read the file into a dict, alter the fields below, and return the updated dict
    buildhub.json fields that should be changed: download.size, download.date, download.url
    """
    contents = utils.load_json(path)
    installer_name = os.path.basename(installer_path)
    dest = manifest['mapping'][locale][installer_name]['destinations']
    url_prefix = context.config["bucket_config"][context.bucket]["url_prefix"]
    # assume url_prefix is ASCII safe
    url = urllib.parse.quote(urllib.parse.urljoin(manifest["s3_bucket_path"], dest[0]))

    # Update fields
    contents['download']['size'] = utils.get_size(installer_path)
    contents['download']['date'] = str(arrow.utcnow())
    contents['download']['url'] = urllib.parse.urljoin(url_prefix, url)

    return contents
