import logging
import os
import re
import shutil

from copy import deepcopy
from scriptworker import client

from beetmoverscript import utils, script
from beetmoverscript.constants import (IGNORED_UPSTREAM_ARTIFACTS,
                                       INITIAL_RELEASE_PROPS_FILE,
                                       STAGE_PLATFORM_MAP,
                                       RESTRICTED_BUCKET_PATHS)

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
    if not any([s3_bucket_path.startswith(p) for p in RESTRICTED_BUCKET_PATHS[bucket]]):
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


def add_checksums_to_artifacts(context):
    abs_file_path = os.path.join(context.config['artifact_dir'],
                                 'public/target.checksums')
    manifest = generate_checksums_manifest(context)
    utils.write_file(abs_file_path, manifest)


def add_balrog_manifest_to_artifacts(context):
    abs_file_path = os.path.join(context.config['artifact_dir'],
                                 'public/manifest.json')
    utils.write_json(abs_file_path, context.balrog_manifest)


def add_release_props_to_artifacts(context, release_props_filepath):
    abs_file_path = os.path.join(context.config['artifact_dir'],
                                 'public/balrog_props.json')
    shutil.copyfile(release_props_filepath, abs_file_path)


def filter_ignored_artifacts(artifact_paths, ignored_artifacts=IGNORED_UPSTREAM_ARTIFACTS):
    """removes artifacts from ignored list if present in artifact_paths.
    returns remaining items
    """
    return [p for p in artifact_paths if os.path.basename(p) not in ignored_artifacts]


def get_upstream_artifact(context, taskid, path):
    abs_path = os.path.abspath(os.path.join(context.config['work_dir'], 'cot', taskid, path))
    if not os.path.exists(abs_path):
        raise ScriptWorkerTaskException(
            "upstream artifact with path: {}, does not exist".format(abs_path)
        )
    return abs_path


def get_upstream_artifacts(context, preserve_full_paths=False):
    artifacts = {}
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        locale = artifact_dict['locale']
        artifacts[locale] = artifacts.get(locale, {})
        for path in filter_ignored_artifacts(artifact_dict['paths']):
            abs_path = get_upstream_artifact(context, artifact_dict['taskId'], path)
            if preserve_full_paths:
                artifacts[locale][path] = abs_path
            else:
                artifacts[locale][os.path.basename(abs_path)] = abs_path
    return artifacts


def get_release_props(context, platform_mapping=STAGE_PLATFORM_MAP):
    """determined via parsing the Nightly build job's balrog_props.json and
    expanded the properties with props beetmover knows about."""
    payload_properties = context.task.get('payload', {}).get('releaseProperties', None)
    initial_release_props_file = None

    if payload_properties:
        props = payload_properties
        log.debug("Loading release_props from task's payload: {}".format(props))
    else:
        initial_release_props_file = get_initial_release_props_file(context)
        props = utils.load_json(initial_release_props_file)['properties']
        log.warn(
            'Deprecated behavior! This will be gone after Firefox 59 reaches release. Loading release_props from "{}": {}'
            .format(initial_release_props_file, props)
        )

    final_props = update_props(context, props, platform_mapping)
    return (final_props, initial_release_props_file)


def get_initial_release_props_file(context):
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        for path in artifact_dict['paths']:
            if os.path.basename(path) == INITIAL_RELEASE_PROPS_FILE:
                return get_upstream_artifact(context, artifact_dict['taskId'], path)
    raise ScriptWorkerTaskException(
        "could not determine initial release props file from upstreamArtifacts"
    )


def update_props(context, props, platform_mapping):
    """Function to alter the `stage_platform` field from balrog_props to their
    corresponding correct values for certain platforms. Please note that for
    l10n jobs the `stage_platform` field is in fact called `platform` hence
    the defaulting below."""
    props = deepcopy(props)
    # en-US jobs have the platform set in the `stage_platform` field while
    # l10n jobs have it set under `platform`. This is merely an uniformization
    # under the `stage_platform` field that is needed later on in the templates
    stage_platform = props.get("stage_platform", props.get("platform"))
    # XXX Bug 1424482 - until we solve this, we need this hack. Since en-US
    # have at least `stage_platform`, there is a way to tell whether they are
    # devedition related or not. But for l10n jobs, we only have `platform`
    # which is identical to the ones we have for Firefox.

    if ('locale' in context.task['payload'] and
            'devedition' in context.task.get('metadata', {}).get('name', {})):
        stage_platform += "-devedition"
    props["stage_platform"] = stage_platform
    # for some products/platforms this mapping is not needed, hence the default
    props["platform"] = platform_mapping.get(stage_platform, stage_platform)
    return props
