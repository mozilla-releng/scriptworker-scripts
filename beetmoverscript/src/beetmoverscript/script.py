#!/usr/bin/env python
"""Beetmover script
"""
import asyncio
import logging
import mimetypes
import os
import re
import sys
from multiprocessing.pool import ThreadPool

import aiohttp
import boto3
from botocore.exceptions import ClientError
from redo import retry
from scriptworker import client
from scriptworker.exceptions import ScriptWorkerRetryException, ScriptWorkerTaskException
from scriptworker.utils import raise_future_exceptions, retry_async

from beetmoverscript import task
from beetmoverscript.constants import (
    BUILDHUB_ARTIFACT,
    CACHE_CONTROL_MAXAGE,
    INSTALLER_ARTIFACTS,
    MIME_MAP,
    NORMALIZED_BALROG_PLATFORMS,
    PARTNER_REPACK_PRIVATE_REGEXES,
    PARTNER_REPACK_PUBLIC_PREFIX_TMPL,
    PARTNER_REPACK_PUBLIC_REGEXES,
    RELEASE_BRANCHES,
    RELEASE_EXCLUDE,
)
from beetmoverscript.task import (
    add_balrog_manifest_to_artifacts,
    add_checksums_to_artifacts,
    get_release_props,
    get_task_action,
    get_task_bucket,
    get_taskId_from_full_path,
    get_updated_buildhub_artifact,
    get_upstream_artifacts,
    validate_task_schema,
)
from beetmoverscript.utils import (
    exists_or_endswith,
    extract_file_config_from_artifact_map,
    generate_beetmover_manifest,
    get_bucket_name,
    get_bucket_url_prefix,
    get_candidates_prefix,
    get_creds,
    get_hash,
    get_partials_props,
    get_partner_candidates_prefix,
    get_partner_match,
    get_partner_releases_prefix,
    get_product_name,
    get_releases_prefix,
    get_size,
    is_partner_action,
    is_partner_private_task,
    is_partner_public_task,
    is_promotion_action,
    is_release_action,
    matches_exclude,
    write_json,
)

log = logging.getLogger(__name__)


# push_to_nightly {{{1
async def push_to_nightly(context):
    """Push artifacts to a certain location (e.g. nightly/ or candidates/).

    Determine the list of artifacts to be transferred, generate the
    mapping manifest, run some data validations, and upload the bits.

    Upon successful transfer, generate checksums files and manifests to be
    consumed downstream by balrogworkers."""
    context.release_props = get_release_props(context)

    # balrog_manifest is written and uploaded as an artifact which is used by
    # a subsequent balrogworker task in the release graph. Balrogworker uses
    # this manifest to submit release blob info (e.g. mar filename, size, etc)
    context.balrog_manifest = list()

    # Used as a staging area to generate balrog_manifest, so that all the
    # completes and partials for a release end up in the same data structure
    context.raw_balrog_manifest = dict()

    # the checksums manifest is written and uploaded as an artifact which is
    # used by a subsequent signing task and again by another beetmover task to
    # upload it to S3
    context.checksums = dict()

    # TODO: if artifactMap passes schema validation
    if context.task["payload"].get("artifactMap"):
        # determine artifacts to beetmove
        context.artifacts_to_beetmove = get_upstream_artifacts(context, preserve_full_paths=True)
        await move_beets(context, context.artifacts_to_beetmove, artifact_map=context.task["payload"]["artifactMap"])
    else:
        raise ScriptWorkerTaskException("task payload is missing artifactMap")

    #  write balrog_manifest to a file and add it to list of artifacts
    add_balrog_manifest_to_artifacts(context)
    # determine the correct checksum filename and generate it, adding it to
    # the list of artifacts afterwards
    add_checksums_to_artifacts(context)


# direct_push_to_releases {{{1
async def direct_push_to_releases(context):
    """Mobile releases such as Fenix and Focus are a hybrid. They are neither
    maven releases, nor classic releases to be pushed into candidates (and
    then published to mirrors) so they get their own dedicated function.
    These releases will publish directly into S3 under ~releases folder.

    Push artifacts to a certain location => ~releases

    Determine the list of artifacts to be transferred, generate the
    mapping manifest, run some data validations, and upload the bits.
    """
    context.release_props = get_release_props(context)
    context.checksums = dict()  # Needed by downstream calls
    context.raw_balrog_manifest = dict()  # Needed by downstream calls

    context.artifacts_to_beetmove = task.get_upstream_artifacts(context, preserve_full_paths=True)
    await move_beets(context, context.artifacts_to_beetmove, artifact_map=context.task["payload"]["artifactMap"])


# push_to_partner {{{1
async def push_to_partner(context):
    """Push private repack artifacts to a certain location. They can be either
    private (to private S3 buckets) or public (going under regular firefox
    bucket).

    Determine the list of artifacts to be transferred, generate the
    mapping manifest and upload the bits."""
    context.artifacts_to_beetmove = get_upstream_artifacts(context, preserve_full_paths=True)
    context.release_props = get_release_props(context)
    context.checksums = dict()

    mapping_manifest = generate_beetmover_manifest(context)
    await move_partner_beets(context, mapping_manifest)

    add_checksums_to_artifacts(context)


# push_to_releases {{{1
async def push_to_releases(context):
    """Copy artifacts from one S3 location to another.

    Determine the list of artifacts to be copied and transfer them. These
    copies happen in S3 without downloading/reuploading."""
    context.artifacts_to_beetmove = {}
    product = context.task["payload"]["product"]
    build_number = context.task["payload"]["build_number"]
    version = context.task["payload"]["version"]
    context.bucket_name = get_bucket_name(context, product)

    candidates_prefix = get_candidates_prefix(product, version, build_number)
    releases_prefix = get_releases_prefix(product, version)

    creds = get_creds(context)
    s3_resource = boto3.resource("s3", aws_access_key_id=creds["id"], aws_secret_access_key=creds["key"])

    candidates_keys_checksums = list_bucket_objects(context, s3_resource, candidates_prefix)
    releases_keys_checksums = list_bucket_objects(context, s3_resource, releases_prefix)

    if not candidates_keys_checksums:
        raise ScriptWorkerTaskException("No artifacts to copy from {} so there is no reason to continue.".format(candidates_prefix))

    if releases_keys_checksums:
        log.warning("Destination {} already exists with {} keys".format(releases_prefix, len(releases_keys_checksums)))

    # Weed out RELEASE_EXCLUDE matches, but allow partners specified in the payload
    push_partners = context.task["payload"].get("partners", [])
    for k in candidates_keys_checksums.keys():
        if "/partner-repacks/" in k:
            partner_match = get_partner_match(k, candidates_prefix, push_partners)
            if partner_match:
                context.artifacts_to_beetmove[k] = k.replace(
                    get_partner_candidates_prefix(candidates_prefix, partner_match), get_partner_releases_prefix(product, version, partner_match)
                )
            else:
                log.debug("Excluding partner repack {}".format(k))
        elif not matches_exclude(k, RELEASE_EXCLUDE):
            context.artifacts_to_beetmove[k] = k.replace(candidates_prefix, releases_prefix)
        else:
            log.debug("Excluding {}".format(k))

    copy_beets(context, candidates_keys_checksums, releases_keys_checksums)


async def push_to_maven(context):
    """Push artifacts to maven locations expected by clients such as mvn/gradle)

    XXX: This function handles the transfer of artifacts to the maven.mozilla.org repository.
    The artifacts being published come from different projects and are all handled here. For
    example as of Q4 2020, we use this function for beetmover releases coming from
    Android-Components, Glean, Application-Services but also in-tree GeckoView.

    This large variety of beetmover jobs usually implies complex checks to cover
    all possible cornercases. For example it needs to handle both MavenVersion for
    Github projects but also FirefoxVersion for GeckoView in-tree releases.
    """
    context.release_props = get_release_props(context)
    context.checksums = dict()  # Needed by downstream calls
    context.raw_balrog_manifest = dict()  # Needed by downstream calls

    # Version validation
    version = task.get_maven_version(context)
    task.check_maven_artifact_map(context, version)

    # overwrite artifacts_to_beetmove with the declarative artifacts ones
    context.artifacts_to_beetmove = task.get_upstream_artifacts(context, preserve_full_paths=True)
    await move_beets(context, context.artifacts_to_beetmove, artifact_map=context.task["payload"]["artifactMap"])


# copy_beets {{{1
def copy_beets(context, from_keys_checksums, to_keys_checksums):
    creds = get_creds(context)
    boto_client = boto3.client("s3", aws_access_key_id=creds["id"], aws_secret_access_key=creds["key"])

    def worker(item):
        source, destination = item

        def copy_key():
            if destination in to_keys_checksums:
                # compare md5
                if from_keys_checksums[source] != to_keys_checksums[destination]:
                    raise ScriptWorkerTaskException(
                        "{} already exists with different content "
                        "(src etag: {}, dest etag: {}), aborting".format(destination, from_keys_checksums[source], to_keys_checksums[destination])
                    )
                else:
                    log.warning("{} already exists with the same content ({}), " "skipping copy".format(destination, to_keys_checksums[destination]))
            else:
                log.info("Copying {} to {}".format(source, destination))
                boto_client.copy_object(Bucket=context.bucket_name, CopySource={"Bucket": context.bucket_name, "Key": source}, Key=destination)

        return retry(copy_key, sleeptime=5, max_sleeptime=60, retry_exceptions=(ClientError,))

    def find_release_files():
        for source, destination in context.artifacts_to_beetmove.items():
            yield (source, destination)

    pool = ThreadPool(context.config.get("copy_parallelization", 20))
    pool.map(worker, find_release_files())


# list_bucket_objects {{{1
def list_bucket_objects(context, s3_resource, prefix):
    """Return a dict of {Key: MD5}"""
    contents = {}
    bucket = s3_resource.Bucket(context.bucket_name)
    for obj in bucket.objects.filter(Prefix=prefix):
        contents[obj.key] = obj.e_tag.split("-")[0]

    return contents


# action_map {{{1
action_map = {
    "push-to-partner": push_to_partner,
    "push-to-nightly": push_to_nightly,
    # push to candidates is at this point identical to push_to_nightly
    "push-to-candidates": push_to_nightly,
    "push-to-releases": push_to_releases,
    "direct-push-to-releases": direct_push_to_releases,
    "push-to-maven": push_to_maven,
}


# async_main {{{1
async def async_main(context):
    for module in ("botocore", "boto3", "chardet"):
        logging.getLogger(module).setLevel(logging.INFO)

    setup_mimetypes()

    validate_task_schema(context)

    connector = aiohttp.TCPConnector(limit=context.config["aiohttp_max_connections"])
    async with aiohttp.ClientSession(connector=connector) as session:
        context.session = session

        # determine the task bucket and action
        context.bucket = get_task_bucket(context.task, context.config)
        context.action = get_task_action(context.task, context.config, valid_actions=action_map.keys())

        if action_map.get(context.action):
            await action_map[context.action](context)
        else:
            log.critical("Unknown action {}!".format(context.action))
            sys.exit(3)

    log.info("Success!")


# move_beets {{{1
async def move_beets(context, artifacts_to_beetmove, manifest=None, artifact_map=None):
    beets = []

    for locale in artifacts_to_beetmove:

        installer_artifact = ""
        buildhub_artifact_exists = False
        # get path of installer beet
        for artifact in artifacts_to_beetmove[locale]:
            if exists_or_endswith(artifact, INSTALLER_ARTIFACTS):
                installer_artifact = artifact
            if exists_or_endswith(artifact, BUILDHUB_ARTIFACT):
                buildhub_artifact_exists = True

        # throws error if buildhub.json is present and installer isn't
        if not installer_artifact and buildhub_artifact_exists:
            raise ScriptWorkerTaskException("could not determine installer path from task payload")

        # move beets
        for artifact in artifacts_to_beetmove[locale]:
            source = artifacts_to_beetmove[locale][artifact]

            # update buildhub.json file
            # if there is no installer then there will be no buildhub.json artifact
            # in logical coding terms, this means that if installer_path is an empty
            # string, then this if-block is never reached
            if exists_or_endswith(artifact, BUILDHUB_ARTIFACT):
                write_json(
                    source,
                    get_updated_buildhub_artifact(
                        path=source,
                        installer_artifact=installer_artifact,
                        installer_path=artifacts_to_beetmove[locale][installer_artifact],
                        context=context,
                        locale=locale,
                        manifest=manifest,
                        artifact_map=artifact_map,
                    ),
                )

            if artifact_map:
                task_id = get_taskId_from_full_path(source)
                # Should only ever be one (taskId, locale) match.
                map_entry = extract_file_config_from_artifact_map(artifact_map, artifact, task_id, locale)

                artifact_pretty_name = map_entry["checksums_path"]
                destinations = map_entry["destinations"]
                update_balrog_manifest = map_entry.get("update_balrog_manifest", False)
                balrog_format = map_entry.get("balrog_format", "")
                from_buildid = map_entry.get("from_buildid")
            else:
                artifact_pretty_name = manifest["mapping"][locale][artifact]["s3_key"]
                destinations = [os.path.join(manifest["s3_bucket_path"], dest) for dest in manifest["mapping"][locale][artifact]["destinations"]]
                update_balrog_manifest = manifest["mapping"][locale][artifact].get("update_balrog_manifest")
                # Adjust old template format.
                # artifact map specifies these separately.
                # templates say "update_balrog_manifest": true
                # or "update_balrog_manifest": {"format": mozinfo}
                if isinstance(update_balrog_manifest, dict):
                    balrog_format = update_balrog_manifest.get("format")
                    update_balrog_manifest = True
                else:
                    balrog_format = ""
                from_buildid = manifest["mapping"][locale][artifact].get("from_buildid")

            beets.append(
                asyncio.ensure_future(
                    move_beet(
                        context,
                        source,
                        destinations,
                        locale=locale,
                        update_balrog_manifest=update_balrog_manifest,
                        balrog_format=balrog_format,
                        from_buildid=from_buildid,
                        artifact_pretty_name=artifact_pretty_name,
                    )
                )
            )
    await raise_future_exceptions(beets)

    # Fix up balrog manifest. We need an entry with both completes and
    # partials, which is why we store up the data from each moved beet
    # and collate it now.
    for locale, info in context.raw_balrog_manifest.items():
        for format in info["completeInfo"]:
            balrog_entry = enrich_balrog_manifest(context, locale)
            balrog_entry["completeInfo"] = [info["completeInfo"][format]]
            if "partialInfo" in info:
                balrog_entry["partialInfo"] = info["partialInfo"]
            if format:
                balrog_entry["blob_suffix"] = "-{}".format(format)
            context.balrog_manifest.append(balrog_entry)


# move_beet {{{1
async def move_beet(context, source, destinations, locale, update_balrog_manifest, balrog_format, from_buildid, artifact_pretty_name):
    await retry_upload(context=context, destinations=destinations, path=source)

    if context.checksums.get(artifact_pretty_name) is None:
        context.checksums[artifact_pretty_name] = {algo: get_hash(source, algo) for algo in context.config["checksums_digests"]}
        context.checksums[artifact_pretty_name]["size"] = get_size(source)

    if update_balrog_manifest:
        context.raw_balrog_manifest.setdefault(locale, {})
        balrog_info = generate_balrog_info(context, artifact_pretty_name, locale, destinations, from_buildid)
        if from_buildid:
            context.raw_balrog_manifest[locale].setdefault("partialInfo", []).append(balrog_info)
        else:
            context.raw_balrog_manifest[locale].setdefault("completeInfo", {})[balrog_format] = balrog_info


# move_partner_beets {{{1
async def move_partner_beets(context, manifest):
    artifacts_to_beetmove = context.artifacts_to_beetmove
    beets = []

    for locale in artifacts_to_beetmove:
        for full_path_artifact in artifacts_to_beetmove[locale]:
            source = artifacts_to_beetmove[locale][full_path_artifact]
            destination = get_destination_for_partner_repack_path(context, manifest, full_path_artifact, locale)
            beets.append(asyncio.ensure_future(upload_to_s3(context=context, s3_key=destination, path=source)))

            if is_partner_public_task(context):
                # we trim the full destination to the part after
                # candidates/{version}-candidates/build{build_number}/
                artifact_pretty_name = destination[destination.find(locale) :]
                if context.checksums.get(artifact_pretty_name) is None:
                    context.checksums[artifact_pretty_name] = {algo: get_hash(source, algo) for algo in context.config["checksums_digests"]}
                    context.checksums[artifact_pretty_name]["size"] = get_size(source)

    await raise_future_exceptions(beets)


def sanity_check_partner_path(path, repl_dict, regexes):
    for regex in regexes:
        regex = regex.format(**repl_dict)
        m = re.match(regex, path)
        if m:
            path_info = m.groupdict()
            for substr in ("partner", "subpartner", "locale"):
                if substr in regex and path_info[substr] in ("..", "."):
                    raise ScriptWorkerTaskException("Illegal partner path {} !".format(path))
            # We're good.
            break
    else:
        raise ScriptWorkerTaskException("Illegal partner path {} !".format(path))


def get_destination_for_partner_repack_path(context, manifest, full_path, locale):
    """Function to process the final destination path, relative to the root of
    the S3 bucket. Depending on whether it's a private or public destination, it
    performs several string manipulations.

    Input: 'releng/partner/ghost/ghost-var/v1/linux-i686/ro/target.tar.bz2'
    Possible output(s):
        -> ghost/59.0b20-2/ghost-variant/v1/linux-i686/en-US/firefox-59.0b20.tar.bz2
        -> pub/firefox/candidates/59.0b20-candidates/build2/partner-repacks/ghost/ghost-variant/v1/linux-i686/en-US/firefox-59.0b20.tar.bz2
    """
    # make sure we're calling this function from private-partner context
    if not is_partner_action(context.action):
        raise ScriptWorkerRetryException("Outside of private-partner context!")

    # pretty name the `target` part to the actual filename
    pretty_full_path = os.path.join(locale, manifest["mapping"][locale][os.path.basename(full_path)])

    build_number = context.task["payload"]["build_number"]
    version = context.task["payload"]["version"]

    if is_partner_private_task(context):
        sanity_check_partner_path(locale, {"version": version, "build_number": build_number}, PARTNER_REPACK_PRIVATE_REGEXES)
        return pretty_full_path
    elif is_partner_public_task(context):
        sanity_check_partner_path(locale, {"version": version, "build_number": build_number}, PARTNER_REPACK_PUBLIC_REGEXES)
        prefix = PARTNER_REPACK_PUBLIC_PREFIX_TMPL.format(version=version, build_number=build_number)
        return os.path.join(prefix, pretty_full_path)


# generate_balrog_info {{{1
def generate_balrog_info(context, artifact_pretty_name, locale, destinations, from_buildid=None):
    release_props = context.release_props
    checksums = context.checksums

    url = "{prefix}/{s3_key}".format(prefix=get_bucket_url_prefix(context), s3_key=destinations[0])

    data = {"hash": checksums[artifact_pretty_name][release_props["hashType"]], "size": checksums[artifact_pretty_name]["size"], "url": url}
    if from_buildid:
        data["from_buildid"] = from_buildid
        if is_promotion_action(context.action):
            partials = get_partials_props(context.task)
            for p in partials.values():
                if p["buildid"] == str(from_buildid):
                    data["previousVersion"] = p["previousVersion"]
                    data["previousBuildNumber"] = p["previousBuildNumber"]
                    break

    return data


# enrich_balrog_manifest {{{1
def enrich_balrog_manifest(context, locale):
    release_props = context.release_props

    url_replacements = []
    if release_props["branch"] in RELEASE_BRANCHES:
        url_replacements.append(["http://archive.mozilla.org/pub", "http://download.cdn.mozilla.net/pub"])

    enrich_dict = {
        "appName": get_product_name(release_props["appName"], release_props["stage_platform"]),
        "appVersion": release_props["appVersion"],
        "branch": release_props["branch"],
        "buildid": release_props["buildid"],
        "extVersion": release_props["appVersion"],
        "hashType": release_props["hashType"],
        "locale": locale if not locale == "multi" else "en-US",
        "platform": NORMALIZED_BALROG_PLATFORMS.get(release_props["stage_platform"], release_props["stage_platform"]),
        "url_replacements": url_replacements,
    }

    if is_promotion_action(context.action) or is_release_action(context.action):
        enrich_dict["tc_release"] = True
        enrich_dict["build_number"] = context.task["payload"]["build_number"]
        enrich_dict["version"] = context.task["payload"]["version"]
    else:
        enrich_dict["tc_nightly"] = True

    return enrich_dict


# retry_upload {{{1
async def retry_upload(context, destinations, path):
    """Manage upload of `path` to `destinations`."""
    uploads = []
    for dest in destinations:
        uploads.append(asyncio.ensure_future(upload_to_s3(context=context, s3_key=dest, path=path)))
    await raise_future_exceptions(uploads)


# put {{{1
async def put(context, url, headers, abs_filename, session=None):
    session = session or context.session
    with open(abs_filename, "rb") as fh:
        async with session.put(url, data=fh, headers=headers, compress=False) as resp:
            log.info("put {}: {}".format(abs_filename, resp.status))
            response_text = await resp.text()
            if response_text:
                log.info(response_text)
            if resp.status not in (200, 204):
                raise ScriptWorkerRetryException("Bad status {}".format(resp.status))
    return resp


# upload_to_s3 {{{1
async def upload_to_s3(context, s3_key, path):
    product = get_product_name(context.release_props["appName"].lower(), context.release_props["stage_platform"])
    mime_type = mimetypes.guess_type(path)[0]
    if not mime_type:
        raise ScriptWorkerTaskException("Unable to discover valid mime-type for path ({}), " "mimetypes.guess_type() returned {}".format(path, mime_type))
    api_kwargs = {"Bucket": get_bucket_name(context, product), "Key": s3_key, "ContentType": mime_type}
    headers = {"Content-Type": mime_type, "Cache-Control": "public, max-age=%d" % CACHE_CONTROL_MAXAGE}
    creds = context.config["bucket_config"][context.bucket]["credentials"]
    s3 = boto3.client("s3", aws_access_key_id=creds["id"], aws_secret_access_key=creds["key"])
    url = s3.generate_presigned_url("put_object", api_kwargs, ExpiresIn=1800, HttpMethod="PUT")

    log.info("upload_to_s3: %s -> s3://%s/%s", path, api_kwargs.get("Bucket"), s3_key)
    await retry_async(put, args=(context, url, headers, path), retry_exceptions=(Exception,), kwargs={"session": context.session})


def setup_mimetypes():
    mimetypes.init()
    # in py3 we must exhaust the map so that add_type is actually invoked
    list(map(lambda ext_mimetype: mimetypes.add_type(ext_mimetype[1], ext_mimetype[0]), MIME_MAP.items()))


def main(config_path=None):
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    default_config = {
        "schema_file": os.path.join(data_dir, "beetmover_task_schema.json"),
        "release_schema_file": os.path.join(data_dir, "release_beetmover_task_schema.json"),
        "maven_schema_file": os.path.join(data_dir, "maven_beetmover_task_schema.json"),
        "artifactMap_schema_file": os.path.join(data_dir, "artifactMap_beetmover_task_schema.json"),
    }

    # There are several task schema. Validation occurs in async_main
    client.sync_main(async_main, config_path=config_path, default_config=default_config, should_validate_task=False)


__name__ == "__main__" and main()
