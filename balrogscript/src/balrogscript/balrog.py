import logging
import pprint
from copy import deepcopy

from balrogclient import Rule
from redo import retry

# from requests.exceptions import HTTPError

log = logging.getLogger(__name__)


def update_existing_rule(rule_data, api_root, dummy, auth0_secrets):
    """Update an existing rule."""
    # XXX should we pass in the Rule or ScheduledRuleChange object, for clean arch?
    rule_id = rule_data.pop("rule_id")  # XXX better error than a KeyError?
    # XXX scheduled_change support?
    rule_obj = Rule(api_root=api_root, auth0_secrets=auth0_secrets, rule_id=rule_id)
    existing_data, existing_data_version = Rule.get_data()  # XXX verify this works
    log.info("Rule %s data version %s:\n%s", rule_id, existing_data_version, pprint.pformat(existing_data))
    # XXX fallbackMapping support?
    # XXX support creation of rules?
    # XXX any verification here?
    #     only support allowlisted products/channels?
    log.info("Updating rule %s with data\n%s", rule_id, pprint.pformat(rule_data))
    # XXX ScheduledRuleChange.add_scheduled_rule_change
    retry(rule_obj.update_rule, kwargs=rule_data, sleeptime=2, max_sleeptime=2, attempts=10)


def create_rule(rule_data, api_root, dummy, auth0_secrets):
    """Create a rule that doesn't exist."""
    raise NotImplementedError("create_rule not written yet")


def delete_existing_rule(rule_data, api_root, dummy, auth0_secrets):
    """"""
    raise NotImplementedError("delete_existing_rule not written yet")


def update_rules(rules, api_root, dummy, auth0_secrets):
    """"""
    # XXX rules api is only api v1??
    for rule in rules:
        rule_data = deepcopy(rule)
        if rule_data.pop("existingRule", True):
            # XXX deletion support? Check for bool, write+call delete_existing_rule
            update_existing_rule(rule_data, api_root, dummy, auth0_secrets)
        else:
            create_rule(rule_data, api_root, dummy, auth0_secrets)
