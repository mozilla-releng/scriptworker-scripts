import json
import logging
import os
import re
import shutil
import scriptworker.client
from beetmoverscript.constants import (IGNORED_UPSTREAM_ARTIFACTS,
                                       INITIAL_RELEASE_PROPS_FILE,
                                       RESTRICTED_ACTIONS)

from beetmoverscript.utils import write_json, write_file
from scriptworker.exceptions import ScriptWorkerTaskException

log = logging.getLogger(__name__)


def validate_task_schema(context):
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)


def get_task_cert_type(task):
    """Extract task certificate type"""
    certs = [s.split(':')[-1] for s in task["scopes"] if
             s.startswith("project:releng:beetmover:cert:")]
    log.info("Certificate types: %s", certs)
    if len(certs) != 1:
        raise ScriptWorkerTaskException("Only one certificate type can be used")

    signing_cert_name = certs[0]
    if re.search('^[0-9A-Za-z_-]+$', signing_cert_name) is None:
        raise ScriptWorkerTaskException("Scope {} is malformed".format(certs[0]))

    if signing_cert_name not in RESTRICTED_ACTIONS.keys():
        raise ScriptWorkerTaskException("Invalid scope")

    return signing_cert_name


def get_task_beetmover_action(cert, task):
    """Extract last part of beetmover action scope"""
    actions = [s.split(":")[-1] for s in task["scopes"] if
               s.startswith("project:releng:beetmover:action:")]

    log.info("Action types: %s", actions)
    if len(actions) != 1:
        raise ScriptWorkerTaskException("Only one action type can be used")

    action = actions[0]
    if action not in RESTRICTED_ACTIONS[cert]:
        raise ScriptWorkerTaskException("Invalid action for {} cert".format(cert))

    return action


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
