import logging
import re

from scriptworker import client
from scriptworker.exceptions import (
    ScriptWorkerTaskException, TaskVerificationError
)
from scriptworker.utils import retry_request
from mozilla_version.gecko import GeckoVersion
from bouncerscript.constants import (
    ALIASES_REGEXES, PRODUCT_TO_DESTINATIONS_REGEXES, PRODUCT_TO_PRODUCT_ENTRY,
    GO_BOUNCER_URL_TMPL, BOUNCER_PATH_REGEXES_PER_PRODUCT,
)

log = logging.getLogger(__name__)


def get_task_server(task, script_config):
    """Extract task server scope from scopes"""
    server_scopes = [
        s for s in task["scopes"] if
        s.startswith(script_config["taskcluster_scope_prefix"] + "server:")
    ]
    log.info("Servers scopes: %s", server_scopes)
    messages = []

    if len(server_scopes) != 1:
        messages.append("One and only one server can be used")
    server_scope = server_scopes[0]
    server = server_scope.split(':')[-1]
    if re.search('^[0-9A-Za-z_-]+$', server) is None:
        messages.append("Server {} is malformed".format(server))

    if server_scope not in script_config['bouncer_config']:
        messages.append("Invalid server scope")

    if messages:
        raise ScriptWorkerTaskException('\n'.join(messages))

    return server_scope


def get_task_action(task, script_config):
    """Extract last part of bouncer action scope"""
    actions = [
        s.split(":")[-1] for s in task["scopes"] if
        s.startswith(script_config["taskcluster_scope_prefix"] + "action:")
    ]

    log.info("Action types: %s", actions)
    messages = []
    if len(actions) != 1:
        messages.append("One and only one action type can be used")

    action = actions[0]
    if action not in get_supported_actions(script_config):
        messages.append("Invalid action scope")

    if messages:
        raise ScriptWorkerTaskException('\n'.join(messages))

    return action


def matches(name, pattern, fullmatch=False):
    if fullmatch:
        return re.fullmatch(pattern, name)
    return re.match(pattern, name)


def get_supported_actions(script_config):
    return tuple(script_config['schema_files'].keys())


def validate_task_schema(context):
    """Perform a schema validation check against taks definition"""
    action = get_task_action(context.task, context.config)
    schema_key = "schema_files.{}".format(action)
    client.validate_task_schema(context, schema_key=schema_key)


def check_product_names_match_aliases(context):
    """Make sure we don't do any cross-product/channel alias update"""
    aliases = context.task["payload"]["aliases_entries"]

    validations = []
    for alias, product_name in aliases.items():
        if alias not in ALIASES_REGEXES.keys():
            raise TaskVerificationError("Unrecognized alias:{}".format(alias))

        validations.append(matches(product_name, ALIASES_REGEXES[alias]))

    if not all(validations):
        raise TaskVerificationError("The product/alias pairs are corrupt: {}".format(aliases))


def check_product_names_match_nightly_locations(context):
    """Double check that nightly products are as expected"""
    products = context.task["payload"]["bouncer_products"]
    if sorted(products) != sorted(BOUNCER_PATH_REGEXES_PER_PRODUCT.keys()):
        raise TaskVerificationError("Products {} don't correspond to nightly ones".format(products))


def check_locations_match(locations, product_config):
    """Function to validate if the payload locations match the ones returned
    from bouncer"""
    if not sorted(locations) == sorted(product_config.values()):
        raise ScriptWorkerTaskException("Bouncer entries are corrupt")


def check_location_path_matches_destination(product_name, path):
    if matches(path,
               BOUNCER_PATH_REGEXES_PER_PRODUCT[product_name],
               fullmatch=True) is None:
        err_msg = ("Corrupt location for product {} "
                   "path {}".format(product_name, path))
        raise ScriptWorkerTaskException(err_msg)


def check_versions_are_successive(current_version, payload_version):
    current_bouncer_version = GeckoVersion.parse(current_version)
    candidate_version = GeckoVersion.parse(payload_version)

    if current_bouncer_version.major_number == candidate_version.major_number:
        err_msg = ("At this point, in-tree version can't be equal to bouncer "
                   "counterpart".format(payload_version, current_version))
        raise ScriptWorkerTaskException(err_msg)
    elif current_bouncer_version.major_number > candidate_version.major_number:
        err_msg = ("In-tree version {} can't be less than current bouncer "
                   "counterpart".format(payload_version, current_version))
        raise ScriptWorkerTaskException(err_msg)
    elif (candidate_version.major_number - current_bouncer_version.major_number) > 1:
        err_msg = ("In-tree version {} can't be greater than current bouncer "
                   "by more than 1 digit".format(payload_version, current_version))
        raise ScriptWorkerTaskException(err_msg)

    log.info("Versions are successive. All good")


def check_path_matches_destination(product_name, path):
    """Function to ensure that the paths to-be-submitted in bouncer are valid
    and according to the in-tree product"""
    possible_products = [p for p, pattern in PRODUCT_TO_PRODUCT_ENTRY if
                         matches(product_name, pattern)]
    product = possible_products[0]
    regex_for_product = PRODUCT_TO_DESTINATIONS_REGEXES[product]
    if matches(path, regex_for_product, fullmatch=True) is None:
        raise ScriptWorkerTaskException(
            'Path "{}" for product "{}" does not match regex: {}'.format(
                product_name, path, regex_for_product
            )
        )


async def check_aliases_match(context):
    """Function to ensure the values returned by bouncer are the same as the
    ones pushed in the `bouncer aliases` job"""
    aliases = context.task["payload"]["aliases_entries"]

    for alias, product_name in aliases.items():
        log.info("Checking alias {} ...".format(alias))
        alias_url = GO_BOUNCER_URL_TMPL.format(alias)
        alias_resp = await retry_request(context, alias_url, good=(200, 404))
        if alias_resp == "404 page not found\n":
            # some of the aliases are expected to be 404 (e.g. `fennec-latest`
            # `fennec-beta-latest`, `thunderbird-next-latest, etc
            continue
        log.info("Alias {} returned url: {}".format(alias, alias_resp))

        log.info("Checking product {} ...".format(product_name))
        product_url = GO_BOUNCER_URL_TMPL.format(product_name)
        product_resp = await retry_request(context, product_url)
        log.info("Product {} returned url: {}".format(product_name, product_resp))

        if alias_resp != product_resp:
            raise ScriptWorkerTaskException("Alias {} and product {} differ!".format(alias, product_name))


def check_version_matches_nightly_regex(version):
    version = GeckoVersion.parse(version)
    if not version.is_nightly:
        raise ScriptWorkerTaskException("Version {} is valid but does not match a nightly one".format(version))
