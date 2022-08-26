import logging
import re

from mozilla_version.gecko import FirefoxVersion, ThunderbirdVersion
from scriptworker import client
from scriptworker.exceptions import ScriptWorkerTaskException, TaskVerificationError
from scriptworker.utils import retry_request

from bouncerscript.constants import (
    ALIASES_REGEXES,
    BOUNCER_PATH_REGEXES_PER_PRODUCT,
    GO_BOUNCER_URL_TMPL,
    PARTNER_ALIASES_REGEX,
    PRODUCT_TO_DESTINATIONS_REGEXES,
    PRODUCT_TO_PRODUCT_ENTRY,
)

log = logging.getLogger(__name__)


version_map = {
    "firefox": FirefoxVersion,
    "thunderbird": ThunderbirdVersion,
}


def get_task_server(task, script_config):
    """Extract task server scope from scopes"""
    server_scopes = [s for s in task["scopes"] if s.startswith(script_config["taskcluster_scope_prefix"] + "server:")]
    log.info("Servers scopes: %s", server_scopes)
    messages = []

    if len(server_scopes) != 1:
        messages.append("One and only one server can be used")
    server_scope = server_scopes[0]
    server = server_scope.split(":")[-1]
    if re.search("^[0-9A-Za-z_-]+$", server) is None:
        messages.append("Server {} is malformed".format(server))

    if server_scope not in script_config["bouncer_config"]:
        messages.append("Invalid server scope")

    if messages:
        raise ScriptWorkerTaskException("\n".join(messages))

    return server_scope


def get_task_action(task, script_config):
    """Extract last part of bouncer action scope"""
    actions = [s.split(":")[-1] for s in task["scopes"] if s.startswith(script_config["taskcluster_scope_prefix"] + "action:")]

    log.info("Action types: %s", actions)
    messages = []
    if len(actions) != 1:
        messages.append("One and only one action type can be used")

    action = actions[0]
    if action not in get_supported_actions(script_config):
        messages.append("Invalid action scope")

    if messages:
        raise ScriptWorkerTaskException("\n".join(messages))

    return action


def matches(name, pattern, fullmatch=False):
    if fullmatch:
        return re.fullmatch(pattern, name)
    return re.match(pattern, name)


def matches_partner_regex(alias, product_name):
    for alias_pattern, product_pattern in PARTNER_ALIASES_REGEX.items():
        alias_match = re.match(alias_pattern, alias)
        product_match = re.match(product_pattern, product_name)
        if alias_match and product_match and alias_match.groups()[0] == product_match.groups()[0]:
            return True
    return False


def get_supported_actions(script_config):
    return tuple(script_config["schema_files"].keys())


def validate_task_schema(context):
    """Perform a schema validation check against task definition"""
    action = get_task_action(context.task, context.config)
    schema_key = "schema_files.{}".format(action)
    client.validate_task_schema(context, schema_key=schema_key)


def check_product_names_match_aliases(context):
    """Make sure we don't do any cross-product/channel alias update"""
    aliases = context.task["payload"]["aliases_entries"]
    all_partner_aliases = "|".join(PARTNER_ALIASES_REGEX.keys())

    validations = []
    for alias, product_name in aliases.items():
        if alias in ALIASES_REGEXES.keys():
            validations.append(matches(product_name, ALIASES_REGEXES[alias]))
        elif re.match(all_partner_aliases, alias):
            validations.append(matches_partner_regex(alias, product_name))
        else:
            raise TaskVerificationError("Unrecognized alias:{}".format(alias))

    if not all(validations):
        raise TaskVerificationError("The product/alias pairs are corrupt: {}".format(aliases))


def check_product_names_match_nightly_locations(context):
    """Double check that nightly products are as expected"""
    products = context.task["payload"]["bouncer_products"]
    valid_sets = []
    for product_set in BOUNCER_PATH_REGEXES_PER_PRODUCT:
        valid_sets.append(sorted(product_set.keys()))
    if sorted(products) not in valid_sets:
        raise TaskVerificationError("Products {} don't correspond to nightly ones".format(products))


def check_locations_match(locations, product_config):
    """Function to validate if the payload locations match the ones returned
    from bouncer"""
    if not sorted(locations) == sorted(product_config.values()):
        raise ScriptWorkerTaskException("Bouncer entries are corrupt")


def check_location_path_matches_destination(product_name, path):
    match = None
    for product_regex in BOUNCER_PATH_REGEXES_PER_PRODUCT:
        if product_name not in product_regex:
            continue
        match = matches(path, product_regex[product_name], fullmatch=True)
        if match:
            break  # Nothing more to check
    if match is None:
        err_msg = "Corrupt location for product {} " "path {}".format(product_name, path)
        raise ScriptWorkerTaskException(err_msg)


def check_versions_are_successive(current_version, payload_version, product):
    """Function to check if the provided version in the payload and the existing
    one in bouncer are successive as valid versions."""

    def _successive_sanity(current_identifier, candidate_identifier):
        if current_identifier == candidate_identifier:
            err_msg = "Identifiers for {} and {} can't be equal at this point in the code".format(payload_version, current_version)
            raise ScriptWorkerTaskException(err_msg)
        elif current_identifier > candidate_identifier:
            err_msg = "In-tree version {} can't be less than current bouncer {} counterpart".format(payload_version, current_version)
            raise ScriptWorkerTaskException(err_msg)
        elif (candidate_identifier - current_identifier) > 1:
            err_msg = "In-tree version {} can't be greater than current bouncer {} by more than 1 digit".format(payload_version, current_version)
            raise ScriptWorkerTaskException(err_msg)

    # XXX: for Firefox central nightlies we need to handle the major number
    # while for Fennec nightlies on ESR we need to handle minor_number
    if product in version_map:
        current_bouncer_version = version_map[product].parse(current_version)
        candidate_version = version_map[product].parse(payload_version)

        _successive_sanity(current_bouncer_version.major_number, candidate_version.major_number)
    else:
        err_msg = "Unknown product {} in the payload".format(product)
        raise ScriptWorkerTaskException(err_msg)

    log.info("Versions are successive. All good")


def check_path_matches_destination(product_name, path):
    """Function to ensure that the paths to-be-submitted in bouncer are valid
    and according to the in-tree product"""
    possible_products = [p for p, pattern in PRODUCT_TO_PRODUCT_ENTRY if matches(product_name, pattern)]
    product = possible_products[0]
    regex_for_product = PRODUCT_TO_DESTINATIONS_REGEXES[product]
    if matches(path, regex_for_product, fullmatch=True) is None:
        raise ScriptWorkerTaskException('Path "{}" for product "{}" does not match regex: {}'.format(product_name, path, regex_for_product))


async def check_aliases_match(context):
    """Function to ensure the values returned by bouncer are the same as the
    ones pushed in the `bouncer aliases` job"""
    aliases = context.task["payload"]["aliases_entries"]
    url_template = GO_BOUNCER_URL_TMPL[context.server]

    for alias, product_name in aliases.items():
        log.info("Checking alias {} ...".format(alias))
        alias_url = url_template.format(alias)
        alias_resp = await retry_request(context, alias_url, good=(200, 404))
        if alias_resp == "404 page not found\n":
            # some of the aliases are expected to be 404 (e.g. `fennec-latest`
            # `fennec-beta-latest`, `thunderbird-next-latest, etc
            continue
        log.info("Alias {} returned url: {}".format(alias, alias_resp))

        log.info("Checking product {} ...".format(product_name))
        product_url = url_template.format(product_name)
        product_resp = await retry_request(context, product_url)
        log.info("Product {} returned url: {}".format(product_name, product_resp))

        if alias_resp != product_resp:
            raise ScriptWorkerTaskException("Alias {} and product {} differ!".format(alias, product_name))


def check_version_matches_nightly_regex(version, product):
    version = version_map[product].parse(version)
    if not version.is_nightly:
        raise ScriptWorkerTaskException("Version {} is valid but does not match a nightly one".format(version))
