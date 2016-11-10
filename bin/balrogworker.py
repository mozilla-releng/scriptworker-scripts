#!/usr/bin/env python
import os
import logging
import argparse
import json
import sys
import hashlib
import requests
from copy import deepcopy
import tempfile
from boto.s3.connection import S3Connection
from mardor.marfile import MarFile

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "../tools/lib/python"
))

from balrog.submitter.cli import NightlySubmitterV4, ReleaseSubmitterV4
from util.retry import retry, retriable

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


def verify_copy_to_s3(args, mar_url, mar_dest):
    # For local development, send TC url directly
    if args.disable_s3:
        return mar_url

    conn = S3Connection(args.aws_key_id, args.aws_key_secret)
    bucket = conn.get_bucket(args.s3_bucket)
    _, dest = tempfile.mkstemp()
    log.info("Downloading %s to %s...", mar_url, dest)
    download(mar_url, dest)
    log.info("Verifying the signature...")
    if not args.disable_certs:
        verify_signature(dest, args.signing_cert)

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


@retriable()
def get_manifest(parent_url):
    manifest_url = parent_url + '/manifest.json'
    log.info("Downloading manifest file from parent: %s" % manifest_url)
    data = requests.get(manifest_url).content.decode('utf-8')
    log.debug("Parsing returned manifest file")
    manifest = json.loads(data)
    return manifest


def verify_task_schema(task_definition):
    task_reqs = ('parent_task_artifacts_url', 'signing_cert')
    for req in task_reqs:
        if req not in task_definition['payload']:
            raise KeyError('%s missing from taskdef!' % req)

    signing_keys = ('nightly', 'release', 'dep')
    if task_definition['payload']['signing_cert'] not in signing_keys:
        raise KeyError('%s invalid certificate name. Specify nightly, release, or dep.'
                       % task_definition['payload']['signing_cert'])


def load_task(task_file):
    with open(task_file, 'r') as f:
        task_definition = json.load(f)

    verify_task_schema(task_definition)
    parent_url = task_definition['payload']['parent_task_artifacts_url']
    signing_cert_name = task_definition['payload']['signing_cert']
    bin_directory = os.path.dirname(os.path.abspath(__file__))
    signing_cert = os.path.join(bin_directory, "../keys/{}.pubkey".format(signing_cert_name))
    return parent_url, signing_cert


def create_submitter(e, balrog_auth, args):
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
        submitter = ReleaseSubmitterV4(api_root=args.api_root,
                                       auth=auth,
                                       dummy=args.dummy)

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

    elif "tc_fennec_nightly" in e:
        log.info("Taskcluster Nightly Fennec style Balrog submission")

        complete_info = e['completeInfo']
        complete_info[0]["url"] = verify_copy_to_s3(args, complete_info[0]['url'], '')
        submitter = NightlySubmitterV4(api_root=args.api_root, auth=auth, dummy=args.dummy,
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


def verify_args(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("--taskdef", required=True,
                        help="File location of task graph"),
    parser.add_argument("-d", "--dummy", action="store_true",
                        help="Add '-dummy' suffix to branch name")
    parser.add_argument("-v", "--verbose", action="store_const",
                        dest="loglevel", const=logging.DEBUG,
                        default=logging.INFO)
    parser.add_argument("--balrog-api-root", default=os.environ.get("BALROG_API_ROOT"),
                        dest="api_root", help="Balrog api url")
    parser.add_argument("--balrog-username", default=os.environ.get("BALROG_USERNAME"),
                        dest="balrog_username", help="Balrog admin api username")
    parser.add_argument("--balrog-password", default=os.environ.get("BALROG_PASSWORD"),
                        dest="balrog_password", help="Balrog admin api password")
    parser.add_argument("--s3-bucket", default=os.environ.get("S3_BUCKET"),
                        dest="s3_bucket", help="S3 Bucket Name: used for uploading partials")
    parser.add_argument("--aws-access-key-id", default=os.environ.get("AWS_ACCESS_KEY_ID"),
                        dest="aws_key_id", help="AWS Access Key ID: S3 Credentials")
    parser.add_argument("--aws-secret-access-key", default=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                        dest="aws_key_secret", help="AWS Secret Key: S3 Credentials")
    parser.add_argument("--disable-s3", default=False, action='store_true',
                        help="Instead of uploading artifacts to S3, send balrog the tc artifact url")
    parser.add_argument("--disable-certs", dest="disable_certs", action="store_true",
                        help="Disable mar signature verification")

    args = parser.parse_args(argv)

    # Disable uploading to S3 if any of the credentials are missing, or if specified as a cli argument
    args.disable_s3 = args.disable_s3 or not (args.s3_bucket and args.aws_key_id and args.aws_key_secret)
    if args.disable_s3:
        log.info("Skipping S3 uploads, submitting taskcluster artifact urls instead.")

    args.parent_url, args.signing_cert = load_task(args.taskdef)

    return args

def update_args_by_popping_balrog_creds(args):
    """Pops balrog auth creds from args and retrieves them"""
    username, password = (args.balrog_username, args.balrog_password)

    new_args = deepcopy(args)
    del(new_args.balrog_username)
    del(new_args.balrog_password)

    return ((username, password), new_args)


def main():
    args = verify_args(sys.argv[1:])
    balrog_auth, args = update_args_by_popping_balrog_creds(args)

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                        stream=sys.stdout,
                        level=args.loglevel)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("boto").setLevel(logging.WARNING)

    # Download the manifest.json from the provided task
    manifest = get_manifest(args.parent_url)

    for e in manifest:
        # Get release metadata from manifest, and upload to S3 if necessary
        submitter, release = create_submitter(e, balrog_auth, args)
        # Connect to balrog and submit the metadata
        retry(lambda: submitter.run(**release))


if __name__ == '__main__':
    main()
