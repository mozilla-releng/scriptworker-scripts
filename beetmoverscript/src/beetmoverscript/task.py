import logging
import os
import re
import urllib.parse
from copy import deepcopy

import arrow
from mozilla_version.errors import PatternNotMatchedError
from mozilla_version.gecko import FirefoxVersion
from mozilla_version.maven import MavenVersion
from scriptworker import artifacts as scriptworker_artifacts
from scriptworker import client
from scriptworker.exceptions import ScriptWorkerTaskException

from beetmoverscript import utils
from beetmoverscript.constants import CHECKSUMS_CUSTOM_FILE_NAMING, STAGE_PLATFORM_MAP

log = logging.getLogger(__name__)


def get_schema_key_by_action(context):
    action = get_task_action(context.task, context.config)
    if utils.is_release_action(action):
        return "release_schema_file"
    elif utils.is_maven_action(action):
        return "maven_schema_file"
    elif utils.is_direct_release_action(action):
        return "artifactMap_schema_file"

    return "schema_file"


def validate_task_schema(context):
    """Perform a schema validation check against task definition"""
    schema_key = get_schema_key_by_action(context)
    client.validate_task_schema(context, schema_key=schema_key)


def _get_bucket_prefixes(script_config):
    return _get_scope_prefixes(script_config, "bucket")


def _get_action_prefixes(script_config):
    return _get_scope_prefixes(script_config, "action")


def _get_scope_prefixes(script_config, sub_namespace):
    prefixes = script_config["taskcluster_scope_prefixes"]
    prefixes = [prefix if prefix.endswith(":") else "{}:".format(prefix) for prefix in prefixes]
    return ["{}{}:".format(prefix, sub_namespace) for prefix in prefixes]


def _extract_scopes_from_unique_prefix(scopes, prefixes):
    scopes = [scope for scope in scopes for prefix in prefixes if scope.startswith(prefix)]
    _check_scopes_exist_and_all_have_the_same_prefix(scopes, prefixes)
    return scopes


def _check_scopes_exist_and_all_have_the_same_prefix(scopes, prefixes):
    for prefix in prefixes:
        if all(scope.startswith(prefix) for scope in scopes):
            break
    else:
        raise ScriptWorkerTaskException("Scopes must exist and all have the same prefix. " "Given scopes: {}. Allowed prefixes: {}".format(scopes, prefixes))


def get_task_bucket(task, script_config):
    """Extract task bucket from scopes"""
    prefixes = _get_bucket_prefixes(script_config)
    scopes = _extract_scopes_from_unique_prefix(task["scopes"], prefixes=prefixes)
    buckets = [s.split(":")[-1] for s in scopes for p in prefixes if s.startswith(p)]
    log.info("Buckets: %s", buckets)
    messages = []
    if len(buckets) != 1:
        messages.append("Only one bucket can be used")

    bucket = buckets[0]
    if re.search("^[0-9A-Za-z_-]+$", bucket) is None:
        messages.append("Bucket {} is malformed".format(bucket))

    if bucket not in script_config["bucket_config"]:
        messages.append("Invalid bucket scope")

    if messages:
        raise ScriptWorkerTaskException("\n".join(messages))

    return bucket


def get_task_action(task, script_config, valid_actions=None):
    """Extract last part of beetmover action scope"""
    prefixes = _get_action_prefixes(script_config)
    scopes = _extract_scopes_from_unique_prefix(task["scopes"], prefixes=prefixes)
    actions = [s.split(":")[-1] for s in scopes for p in prefixes if s.startswith(p)]

    log.info("Action types: %s", actions)
    messages = []
    if len(actions) != 1:
        messages.append("Only one action type can be used")

    action = actions[0]
    if valid_actions is not None and action not in valid_actions:
        messages.append("Invalid action scope")

    if messages:
        raise ScriptWorkerTaskException("\n".join(messages))

    return action


def get_maven_version(context):
    """Extract and validate a valid Maven version"""
    version = context.task["payload"]["version"]
    release_props = context.release_props
    # TODO The following 'if' should be removed once GeckoView >= 84 is in mozilla-release.
    # This is a temporary solution to maintain compatibility while the 'version' field in
    # GeckoView's payload transitions from FirefoxVersion format to MavenVersion.
    if release_props.get("appName") == "geckoview":
        app_version = FirefoxVersion.parse(release_props["appVersion"])
        if int(app_version.major_number) < 84:
            # Change version number to major.minor.buildId because that's what the build task produces
            version = "{}.{}.{}".format(app_version.major_number, app_version.minor_number, release_props["buildid"])

    # Check that version is a valid maven version
    try:
        MavenVersion.parse(version)
    except (ValueError, PatternNotMatchedError) as e:
        raise ScriptWorkerTaskException(f"Version defined in the payload does not match the pattern of a MavenVersion. Got: {version}") from e

    return version


def check_maven_artifact_map(context, version):
    """Check that versions in artifact map are consistent with a given version"""
    for artifact_dict in context.task["payload"]["artifactMap"]:
        for dest_dict in artifact_dict["paths"].values():
            for dest in dest_dict["destinations"]:
                dest_folder, dest_file = os.path.split(dest)
                last_folder = os.path.basename(dest_folder)
                if version != last_folder:
                    raise ScriptWorkerTaskException(f"Name of last folder '{last_folder}' in path '{dest}' does not match payload version '{version}'")
                if version not in dest_file:
                    raise ScriptWorkerTaskException(f"Cannot find version '{version}' in file name '{dest_file}'. Path under test: {dest}")


def generate_checksums_manifest(context):
    checksums_dict = context.checksums
    content = list()
    for artifact, values in sorted(checksums_dict.items()):
        for algo in context.config["checksums_digests"]:
            content.append("{} {} {} {}".format(values[algo], algo, values["size"], artifact))

    return "\n".join(content)


def is_custom_checksums_task(context):
    return CHECKSUMS_CUSTOM_FILE_NAMING.get(context.task["tags"]["kind"], "")


def add_checksums_to_artifacts(context):
    name = is_custom_checksums_task(context)
    filename = "public/target{}.checksums".format(name)

    abs_file_path = os.path.join(context.config["artifact_dir"], filename)
    manifest = generate_checksums_manifest(context)
    utils.write_file(abs_file_path, manifest)


def add_balrog_manifest_to_artifacts(context):
    abs_file_path = os.path.join(context.config["artifact_dir"], "public/manifest.json")
    utils.write_json(abs_file_path, context.balrog_manifest)


def get_upstream_artifacts(context, preserve_full_paths=False):
    artifacts = {}
    for artifact_dict in context.task["payload"]["upstreamArtifacts"]:
        locale = artifact_dict.get("locale", "en-US")
        artifacts[locale] = artifacts.get(locale, {})
        for path in artifact_dict["paths"]:
            abs_path = scriptworker_artifacts.get_and_check_single_upstream_artifact_full_path(context, artifact_dict["taskId"], path)
            if preserve_full_paths:
                artifacts[locale][path] = abs_path
            else:
                artifacts[locale][os.path.basename(abs_path)] = abs_path
    return artifacts


def get_release_props(context, platform_mapping=STAGE_PLATFORM_MAP):
    """determined via parsing the Nightly build job's payload and
    expanded the properties with props beetmover knows about."""
    payload_properties = context.task.get("payload", {}).get("releaseProperties", None)

    if not payload_properties:
        raise ScriptWorkerTaskException("could not determine release props file from task payload")

    log.debug("Loading release_props from task's payload: {}".format(payload_properties))
    return update_props(context, payload_properties, platform_mapping)


def update_props(context, props, platform_mapping):
    """Function to alter slightly the `platform` value and to enrich context with
    `stage_platform` as we need both in the beetmover template manifests."""
    props = deepcopy(props)

    stage_platform = props.get("platform", "")
    # for some products/platforms this mapping is not needed, hence the default
    props["platform"] = platform_mapping.get(stage_platform, stage_platform)
    props["stage_platform"] = stage_platform
    return props


def get_updated_buildhub_artifact(path, installer_artifact, installer_path, context, locale, manifest=None, artifact_map=None):
    """
    Read the file into a dict, alter the fields below, and return the updated dict
    buildhub.json fields that should be changed: download.size, download.date, download.url
    """
    contents = utils.load_json(path)
    url_prefix = context.config["bucket_config"][context.bucket]["url_prefix"]
    if artifact_map:
        task_id = get_taskId_from_full_path(installer_path)
        cfg = utils.extract_file_config_from_artifact_map(artifact_map, installer_artifact, task_id, locale)
        path = urllib.parse.quote(cfg["destinations"][0])
    else:
        dest = manifest["mapping"][locale][installer_artifact]["destinations"][0]
        path = urllib.parse.quote(urllib.parse.urljoin(manifest["s3_bucket_path"], dest))
    url = urllib.parse.urljoin(url_prefix, path)

    # Update fields
    contents["download"]["size"] = utils.get_size(installer_path)
    contents["download"]["date"] = str(arrow.utcnow())
    contents["download"]["url"] = url

    return contents


def get_taskId_from_full_path(full_path_artifact):
    """Temporary fix: Extract the taskId from a full path artifact
    Input: '/src/beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.mozinfo.json'
    Output: 'eSzfNqMZT_mSiQQXu8hyqg'
    """
    split_path = full_path_artifact.split(os.path.sep)
    try:
        cot_dir_index = split_path.index("cot")
        possible_task_id = split_path[cot_dir_index + 1]
        return utils.validated_task_id(possible_task_id)
    except (IndexError, ValueError):
        raise ScriptWorkerTaskException("taskId unable to be extracted from path {}".format(full_path_artifact))
