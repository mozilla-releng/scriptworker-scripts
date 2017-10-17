import json
import logging
import os
import re
import shutil
import scriptworker.client
from beetmoverscript.constants import (IGNORED_UPSTREAM_ARTIFACTS,
                                       INITIAL_RELEASE_PROPS_FILE,
                                       RESTRICTED_BUCKET_PATHS)

from beetmoverscript.utils import write_json, write_file, is_action_a_release_shipping
from scriptworker.exceptions import ScriptWorkerTaskException

log = logging.getLogger(__name__)


def validate_task_schema(context):
    """Perform a schema validation check against taks definition"""
    schema_file = context.config['schema_file']
    action = get_task_action(context.task, context.config)
    if is_action_a_release_shipping(action):
        schema_file = context.config['release_schema_file']
    with open(schema_file) as fh:
        task_schema = json.load(fh)
    scriptworker.client.validate_json_schema(context.task, task_schema)


def get_task_bucket(task, script_config):
    """Extract task bucket from scopes"""
    buckets = [s.split(':')[-1] for s in task["scopes"] if
               s.startswith("project:releng:beetmover:bucket:")]
    log.info("Buckets: %s", buckets)
    if len(buckets) != 1:
        raise ScriptWorkerTaskException("Only one bucket can be used")

    bucket = buckets[0]
    if re.search('^[0-9A-Za-z_-]+$', bucket) is None:
        raise ScriptWorkerTaskException("Bucket {} is malformed".format(bucket))

    if bucket not in script_config['bucket_config']:
        raise ScriptWorkerTaskException("Invalid bucket scope")

    return bucket


def get_task_action(task, script_config):
    """Extract last part of beetmover action scope"""
    actions = [s.split(":")[-1] for s in task["scopes"] if
               s.startswith("project:releng:beetmover:action:")]

    log.info("Action types: %s", actions)
    if len(actions) != 1:
        raise ScriptWorkerTaskException("Only one action type can be used")

    action = actions[0]
    if action not in script_config['actions']:
        raise ScriptWorkerTaskException("Invalid action scope")

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
    write_file(abs_file_path, manifest)


def add_balrog_manifest_to_artifacts(context):
    abs_file_path = os.path.join(context.config['artifact_dir'],
                                 'public/manifest.json')
    write_json(abs_file_path, context.balrog_manifest)


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


def get_upstream_artifacts(context):
    artifacts = {}
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        locale = artifact_dict['locale']
        artifacts[locale] = artifacts.get(locale, {})
        for path in filter_ignored_artifacts(artifact_dict['paths']):
            abs_path = get_upstream_artifact(context, artifact_dict['taskId'], path)
            artifacts[locale][os.path.basename(abs_path)] = abs_path
    return artifacts


def get_initial_release_props_file(context):
    for artifact_dict in context.task['payload']['upstreamArtifacts']:
        for path in artifact_dict['paths']:
            if os.path.basename(path) == INITIAL_RELEASE_PROPS_FILE:
                return get_upstream_artifact(context, artifact_dict['taskId'], path)
    raise ScriptWorkerTaskException(
        "could not determine initial release props file from upstreamArtifacts"
    )
