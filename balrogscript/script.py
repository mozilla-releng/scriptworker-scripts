#!/usr/bin/env python
from copy import deepcopy
import json
import jsonschema
import logging
import os
import re
import sys
from mardor.marfile import MarFile


log = logging.getLogger(__name__)


def verify_signature(mar, signature):
    log.info("Checking %s signature", mar)
    m = MarFile(mar, signature_versions=[(1, signature)])
    m.verify_signatures()


def possible_names(initial_name, amount):
    """Generate names appending counter before extension"""
    prefix, ext = os.path.splitext(initial_name)
    return [initial_name] + ["{}-{}{}".format(prefix, n, ext) for n in
                             range(1, amount + 1)]


def get_manifest(config):
    # assumes a single upstreamArtifact and single path
    task_id = config['upstream_artifacts'][0]['taskId']
    path = os.path.join(config['work_dir'], "cot",
                        task_id, config['upstream_artifacts'][0]['paths'][0])
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


def load_task(config):
    task_file = os.path.join(config['work_dir'], "task.json")
    with open(task_file, 'r') as f:
        task_definition = json.load(f)

    verify_task_schema(config, task_definition)
    upstream_artifacts = task_definition['payload']['upstreamArtifacts']
    for scope in task_definition['scopes']:
        if scope.startswith("project:releng:balrog:"):
            signing_cert_name = scope.split(':')[-1]
            if re.search('^[0-9A-Za-z_-]+$', signing_cert_name) is not None:
                break
            log.warning('scope {} is malformed, skipping!'.format(scope))
    else:
        log.critical("no balrog scopes!")
        sys.exit(3)
    bin_directory = os.path.dirname(os.path.abspath(__file__))
    signing_cert = os.path.join(bin_directory,
                                "keys/{}.pubkey".format(signing_cert_name))
    return upstream_artifacts, signing_cert


def create_submitter(e, balrog_auth, config):
    from balrog.submitter.cli import NightlySubmitterV4, ReleaseSubmitterV4  # noqa: E402
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
        submitter = NightlySubmitterV4(api_root=config['api_root'], auth=auth,
                                       dummy=config['dummy'],
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
        raise RuntimeError("Unknown Balrog submission style. Check manifest.json")


def usage():
    print >> sys.stderr, "Usage: {} CONFIG_FILE".format(sys.argv[0])
    sys.exit(2)


def load_config(argv):
    if len(argv) != 1:
        usage()
    try:
        with open(argv[0]) as fh:
            config = json.load(fh)
    except (ValueError, OSError) as e:
        print >> sys.stderr, "Can't read config file {}!\n{}".format(argv[0], e)
        sys.exit(5)
    except KeyError as e:
        print >> sys.stderr, "Usage: balrogscript CONFIG_FILE\n{}".format(e)
        sys.exit(5)
    return config


def setup_logging(verbose=False):
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                        stream=sys.stdout,
                        level=log_level)
    logging.getLogger("boto").setLevel(logging.WARNING)


def update_config(config):
    config = deepcopy(config)

    for config_key, env_var in {
        "api_root": "BALROG_API_ROOT",
        "balrog_username": "BALROG_USERNAME",
        "balrog_password": "BALROG_PASSWORD",
    }.items():
        config.setdefault(config_key, os.environ.get(env_var))
        if config[config_key] is None:
            log.critical("{} missing from config! (You can also set the env var {})".format(config_key, env_var))
            sys.exit(5)

    config['upstream_artifacts'], config['signing_cert'] = load_task(config)

    # get the balrog creds out of config
    username, password = (config['balrog_username'], config['balrog_password'])
    del(config['balrog_username'])
    del(config['balrog_password'])

    return (username, password), config


def main():
    config = load_config(sys.argv[1:])
    setup_logging(config['verbose'])
    balrog_auth, config = update_config(config)

    # hacking the tools repo dependency by first reading its location from
    # the config file and only then loading the module from subdfolder
    sys.path.insert(0, os.path.join(config['tools_location'], 'lib/python'))
    # Until we get rid of our tools dep, this import(s) will break flake8 E402
    from util.retry import retry  # noqa: E402

    # Read the manifest from disk
    manifest = get_manifest(config)

    for e in manifest:
        # Get release metadata from manifest
        submitter, release = create_submitter(e, balrog_auth, config)
        # Connect to balrog and submit the metadata
        retry(lambda: submitter.run(**release))


if __name__ == '__main__':
    main()
