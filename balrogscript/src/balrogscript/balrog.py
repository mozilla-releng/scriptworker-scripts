import logging
import pprint
from copy import deepcopy

from balrogclient import Rule
from redo import retry

# from requests.exceptions import HTTPError

log = logging.getLogger(__name__)


def update_rules(rules, api_root, dummy, auth0_secrets):
    for rule in rules:
        # XXX get former data? or do we just update the fields mentioned?
        data = deepcopy(rule)
        rule_id = data.pop("rule_id")
        # XXX scheduled_change support?
        # XXX deletion support?
        # XXX fallbackMapping support?
        # XXX support creation of rules?
        # XXX any verification here?
        #     possibly download the existing rule
        #     only support allowlisted products/channels?

        log.info(f"Updating rule {rule_id} with data\n{pprint.pformat(data)}")
        rule_obj = Rule(api_root=api_root, auth0_secrets=auth0_secrets, rule_id=rule_id)
        # ScheduledRuleChange?
        retry(rule_obj.update_rule, kwargs=data, sleeptime=2, max_sleeptime=2, attempts=10)
