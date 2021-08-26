import logging
import pprint
from copy import deepcopy

from balrogclient import Rule, ScheduledRuleChange
from redo import retry

# from requests.exceptions import HTTPError

log = logging.getLogger(__name__)


def update_existing_rule(rule_data, api_root, dummy, auth0_secrets):
    """Update an existing rule."""
    # XXX should we pass in the Rule or ScheduledRuleChange object, for clean arch?
    rule_id = rule_data.pop("rule_id")  # XXX better error than a KeyError?
    scheduled_change = rule_data.pop("scheduledChange", False)
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
    existing_data, existing_data_version = Rule.get_data()  # XXX verify this works
    log.info("Rule %s data version %s:\n%s", rule_id, existing_data_version, pprint.pformat(existing_data))
    # XXX fallbackMapping support?
    log.info("%s rule %s with data\n%s", update_str, rule_id, pprint.pformat(rule_data))
    retry(update_fn, kwargs=rule_data, sleeptime=2, max_sleeptime=2, attempts=10)


def create_rule(rule_data, api_root, dummy, auth0_secrets):
    """Create a rule that doesn't exist."""
    # XXX Scheduled Change support?
    # XXX fallbackMapping support?
    raise NotImplementedError("create_rule not written yet")


def delete_existing_rule(rule_data, api_root, dummy, auth0_secrets):
    """"""
    # XXX Scheduled Change support?
    # http://mozilla-balrog.readthedocs.io/en/latest/admin_api.html#delete
    raise NotImplementedError("delete_existing_rule not written yet")


def update_rules(rules, api_root, dummy, auth0_secrets):
    """"""
    for rule in rules:
        rule_data = deepcopy(rule)
        # XXX any verification here?
        #     only support allowlisted products/channels?
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
