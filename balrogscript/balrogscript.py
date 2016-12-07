#!/usr/bin/env python
import os
import logging
from frozendict import frozendict
import json
import jsonschema
import sys
import hashlib
import requests
import tempfile
from boto.s3.connection import S3Connection
from mardor.marfile import MarFile

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "../tools/lib/python"
))

# Until we get rid of our build/tools dep, this import block will break flake8 E402
from balrog.submitter.cli import NightlySubmitterV4, ReleaseSubmitterV4  # noqa: E402
from util.retry import retry, retriable  # noqa: E402

log = logging.getLogger(__name__)


def get_hash(content, hash_type="md5"):
    h = hashlib.new(hash_type)
    h.update(content)
    return h.hexdigest()


@retriable()
def download(url, dest, mode=None):
    log.debug("Downloading %s to %s", url, dest)
    r = requests.get(url)
    r.raise_for_status()

    bytes_downloaded = 0
    with open(dest, 'wb') as fd:
        for chunk in r.iter_content(4096):
            fd.write(chunk)
            bytes_downloaded += len(chunk)

    log.debug('Downloaded %s bytes', bytes_downloaded)
    if 'content-length' in r.headers:
        log.debug('Content-Length: %s bytes', r.headers['content-length'])
        if bytes_downloaded != int(r.headers['content-length']):
            raise IOError('Unexpected number of bytes downloaded')

    if mode:
        log.debug("chmod %o %s", mode, dest)
        os.chmod(dest, mode)


def verify_signature(mar, signature):
    log.info("Checking %s signature", mar)
    m = MarFile(mar, signature_versions=[(1, signature)])
    m.verify_signatures()


def verify_copy_to_s3(config, mar_url, mar_dest):
    # For local development, send TC url directly
    if config['disable_s3']:
        return mar_url

    conn = S3Connection(config['aws_key_id'], config['aws_key_secret'])
    bucket = conn.get_bucket(config['s3_bucket'])
    _, dest = tempfile.mkstemp()
    log.info("Downloading %s to %s...", mar_url, dest)
    download(mar_url, dest)
    log.info("Verifying the signature...")
    if not config['disable_certs']:
        verify_signature(dest, config['signing_cert'])

    for name in possible_names(mar_dest, 10):
        log.info("Checking if %s already exists", name)
        key = bucket.get_key(name)
        if not key:
            log.info("Uploading to %s...", name)
            key = bucket.new_key(name)
            # There is a chance for race condition here. To avoid it we check
            # the return value with replace=False. It should be not None.
            length = key.set_contents_from_filename(dest, replace=False)
            if length is None:
                log.warn("Name race condition using %s, trying again...", name)
                continue
            else:
                # key.make_public() may lead to race conditions, because
                # it doesn't pass version_id, so it may not set permissions
                bucket.set_canned_acl(acl_str='public-read', key_name=name,
                                      version_id=key.version_id)
                # Use explicit version_id to avoid using "latest" version
                return key.generate_url(expires_in=0, query_auth=False,
                                        version_id=key.version_id)
        else:
            if get_hash(key.get_contents_as_string()) == \
                    get_hash(open(dest).read()):
                log.info("%s has the same MD5 checksum, not uploading...",
                         name)
                return key.generate_url(expires_in=0, query_auth=False,
                                        version_id=key.version_id)
            log.info("%s already exists with different checksum, "
                     "trying another one...", name)

    raise RuntimeError("Cannot generate a unique name for %s. Limit of 10 reached.", mar_dest)


def possible_names(initial_name, amount):
    """Generate names appending counter before extension"""
    prefix, ext = os.path.splitext(initial_name)
    return [initial_name] + ["{}-{}{}".format(prefix, n, ext) for n in
                             range(1, amount + 1)]


def get_manifest(config):
    # assumes a single upstreamArtifact and single path
    task_id = config['upstream_artifacts'][0]['taskId']
    path = os.path.join(config['work_dir'], "cot", task_id, config['upstream_artifacts'][0]['paths'][0])
    log.info("Reading manifest file %s" % path)
    try:
        with open(path, "r") as fh:
            manifest = json.load(fh)
    except (ValueError, OSError) as e:
        log.critical("Can't load manifest from {}!\n{}".format(path, e))
        sys.exit(3)
    return manifest


def verify_task_schema(config, task_definition):
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), config['schema_file']
    )
    with open(schema_path) as fh:
        schema = json.load(fh)

    try:
        jsonschema.validate(task_definition, schema)
    except jsonschema.exceptions.ValidationError as exc:
        log.critical("Can't validate schema!\n{}".format(exc))
        sys.exit(3)


def load_task(config, task_file):
    with open(task_file, 'r') as f:
        task_definition = json.load(f)

    verify_task_schema(config, task_definition)
    upstream_artifacts = task_definition['payload']['upstreamArtifacts']
    for scope in task_definition['scopes']:
        if scope.startswith("project:releng:balrog:"):
            signing_cert_name = scope.split(':')[-1]
            break
    else:
        log.critical("no balrog scopes!")
        sys.exit(3)
    bin_directory = os.path.dirname(os.path.abspath(__file__))
    signing_cert = os.path.join(bin_directory, "keys/{}.pubkey".format(signing_cert_name))
    return upstream_artifacts, signing_cert


def create_submitter(e, balrog_auth, config):
    auth = balrog_auth

    if "previousVersion" in e and "previousBuildNumber" in e:
        log.info("Release style balrog submission")

        complete_info = [{
            "hash": e["to_hash"],
            "size": e["to_size"],
        }]
        partial_info = [{
            "hash": e["hash"],
            "size": e["size"],
        }]
        partial_info[0]["previousVersion"] = e["previousVersion"]
        partial_info[0]["previousBuildNumber"] = e["previousBuildNumber"]
        submitter = ReleaseSubmitterV4(api_root=config['api_root'],
                                       auth=auth,
                                       dummy=config['dummy'])

        return submitter, {'platform': e["platform"],
                           'productName': e["appName"],
                           'version': e["toVersion"],
                           'build_number': e["toBuildNumber"],
                           'appVersion': e["version"],
                           'extVersion': e["version"],
                           'buildID': e["to_buildid"],
                           'locale': e["locale"],
                           'hashFunction': 'sha512',
                           'partialInfo': partial_info,
                           'completeInfo': complete_info}

    elif "tc_nightly" in e:
        log.info("Taskcluster Nightly Fennec style Balrog submission")

        complete_info = e['completeInfo']
        complete_info[0]["url"] = verify_copy_to_s3(config, complete_info[0]['url'], '')
        submitter = NightlySubmitterV4(api_root=config['api_root'], auth=auth, dummy=config['dummy'],
                                       url_replacements=e.get('url_replacements', []))

        return submitter, {'platform': e["platform"],
                           'buildID': e["buildid"],
                           'productName': e["appName"],
                           'branch': e["branch"],
                           'appVersion': e["appVersion"],
                           'locale': e["locale"],
                           'hashFunction': e['hashType'],
                           'extVersion': e["extVersion"],
                           'completeInfo': complete_info}
    else:
        raise RuntimeError("Cannot determine Balrog submission style. Check manifest.json")


def get_config(argv):
    try:
        with open(argv[0]) as fh:
            config = json.load(fh)
    except (ValueError, OSError) as e:
        log.critical("Can't read config file {}!\n{}".format(argv[0], e))
        sys.exit(5)
    except KeyError as e:
        log.critical("Usage: balrogscript CONFIG_FILE\n{}".format(e))
        sys.exit(5)
    for config_key, env_var in {
        "api_root": "BALROG_API_ROOT",
        "balrog_username": "BALROG_USERNAME",
        "balrog_password": "BALROG_PASSWORD",
        "s3_bucket": "S3_BUCKET",
        "aws_key_id": "AWS_ACCESS_KEY_ID",
        "aws_key_secret": "AWS_SECRET_ACCESS_KEY",
    }:
        config.setdefault(config_key, os.environ.get(env_var))
        if config[config_key] is None:
            log.critical("{} missing from config! (You can also set the env var {})".format(config_key, env_var))
            sys.exit(5)

    # Disable uploading to S3 if any of the credentials are missing, or if specified as a cli argument
    config['disable_s3'] = config['disable_s3'] or not (config['s3_bucket'] and config['aws_key_id'] and config['aws_key_secret'])
    if config['disable_s3']:
        log.info("Skipping S3 uploads, submitting taskcluster artifact urls instead.")

    taskdef = os.path.join(config['work_dir'], "task.json")
    config['upstream_artifacts'], config['signing_cert'] = load_task(config, taskdef)

    # get the balrog creds out of config
    username, password = (config['balrog_username'], config['balrog_password'])
    del(config['balrog_username'])
    del(config['balrog_password'])

    return (username, password), frozendict(config)


def main():
    balrog_auth, config = get_config(sys.argv[1:])
    level = logging.INFO
    if config['verbose']:
        level = logging.DEBUG

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                        stream=sys.stdout,
                        level=level)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("boto").setLevel(logging.WARNING)

    # Download the manifest.json from the provided task
    manifest = get_manifest(config)

    for e in manifest:
        # Get release metadata from manifest, and upload to S3 if necessary
        submitter, release = create_submitter(e, balrog_auth, config)
        # Connect to balrog and submit the metadata
        retry(lambda: submitter.run(**release))


if __name__ == '__main__':
    main()
