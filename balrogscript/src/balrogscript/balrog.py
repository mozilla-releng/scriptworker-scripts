import logging
import pprint
from copy import deepcopy

from balrogclient.api import API, Rule, ScheduledRuleChange
from redo import retry

# from requests.exceptions import HTTPError

log = logging.getLogger(__name__)


def existing_api_data(api_obj, name):
    """Call ``get_data`` on an API object and log."""
    existing_data, existing_data_version = api_obj.get_data()  # XXX verify this works
    log.info("%s data version %s:\n%s", name, existing_data_version, pprint.pformat(existing_data))
    return existing_data, existing_data_version


def update_existing_rule(rule_data, api_root, dummy, auth0_secrets):
    """Update an existing rule."""
    rule_id = rule_data.pop("rule_id")  # XXX better error than a KeyError?
    scheduled_change = rule_data.pop("scheduledChange", False)
    # XXX any verification here?
    #     only support allowlisted products/channels?
    if scheduled_change:
        # XXX sc_rule_body ?
        rule_obj = ScheduledRuleChange(api_root=api_root, auth0_secrets=auth0_secrets, rule_id=rule_id)
        update_fn = rule_obj.add_scheduled_rule_change
        update_str = "Scheduling rule change for"
        rule_data["change_type"] = "update"
    else:
        rule_obj = Rule(api_root=api_root, auth0_secrets=auth0_secrets, rule_id=rule_id)
        update_fn = rule_obj.update_rule
        update_str = "Updating"
    existing_api_data(rule_obj, f"Rule {rule_id}")
    log.info("%s rule %s with data\n%s", update_str, rule_id, pprint.pformat(rule_data))
    reply = retry(update_fn, kwargs=rule_data, sleeptime=2, max_sleeptime=2, attempts=10)
    log.info("Reply: {reply}")


def create_rule(rule_data, api_root, dummy, auth0_secrets):
    """Create a rule that doesn't exist."""
    # XXX any verification here?
    #     only support allowlisted products/channels?
    if rule_data.get("rule_id"):
        raise ValueError(f"Cannot specify rule_id in creation!\n{pprint.pformat(rule_data)}")
    api = API(api_root=api_root, auth0_secrets=auth0_secrets)
    if scheduled_change:
        # XXX sc_rule_body ?
        api.rule_template = "/scheduled_changes/rules"
        rule_data["change_type"] = "insert"
        create_str = "Scheduling creation of"
    else:
        api.rule_template = "/rules"
        create_str = "Creating"
    api.rule_template_vars = {}
    api.prerequest_url_template = "/rules"
    kwargs = {"data": rule_data, "method": "POST"}
    log.info("%s rule with data\n%s", create_str, pprint.pformat(rule_data))
    # XXX api.request will try to retrieve the nonexistent rule first.
    #     verify that this isn't an issue
    reply = retry(api.request, kwargs=kwargs, sleeptime=2, max_sleeptime=2, attempts=10)
    log.info("Reply: {reply}")


def delete_existing_rule(rule_data, api_root, dummy, auth0_secrets):
    """Delete an existing rule."""
    # http://mozilla-balrog.readthedocs.io/en/latest/admin_api.html#delete
    # XXX any verification here?
    #     only support allowlisted products/channels?
    rule_id = rule_data.pop("rule_id")  # XXX better error than a KeyError?
    scheduled_change = rule_data.pop("scheduledChange", False)
    if scheduled_change:
        # XXX sc_rule_body ?
        rule_obj = ScheduledRuleChange(api_root=api_root, auth0_secrets=auth0_secrets, rule_id=rule_id)
        rule_data["change_type"] = "delete"
        delete_fn = rule_obj.add_scheduled_rule_change
        delete_str = "Scheduling deletion of"
    else:
        rule_obj = Rule(api_root=api_root, auth0_secrets=auth0_secrets, rule_id=rule_id)
        rule_data["method"] = "DELETE"
        delete_fn = rule_obj.request
        delete_str = "Deleting"
    existing_api_data(rule_obj, f"Rule {rule_id}")
    log.info("%s rule %s with data\n%s", delete_str, rule_id, pprint.pformat(rule_data))
    reply = retry(delete_fn, kwargs=rule_data, sleeptime=2, max_sleeptime=2, attempts=10)
    log.info("Reply: {reply}")


def update_rules(rules, api_root, dummy, auth0_secrets):
    """Create, delete, or update all rules specified in the payload."""
    for rule in rules:
        rule_data = deepcopy(rule)
        delete_rule = rule_data.pop("deleteRule", False)
        if rule_data.pop("existingRule", True):
            if delete_rule:
                delete_existing_rule(rule_data, api_root, dummy, auth0_secrets)
            else:
                update_existing_rule(rule_data, api_root, dummy, auth0_secrets)
        else:
            if delete_rule:
                raise Exception(f"Trying to delete a non-existent rule! {pprint.pformat(rule_data)}")
            create_rule(rule_data, api_root, dummy, auth0_secrets)
