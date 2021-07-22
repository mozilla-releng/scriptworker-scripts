import json
import logging

from balrogclient import Release, ReleaseState, Rule, ScheduledRuleChange, SingleLocale, balrog_request, get_balrog_session
from redo import retry
from requests.exceptions import HTTPError

log = logging.getLogger(__name__)


def update_rules(rules, api_root, dummy, auth0_secrets):
    for rule in rules:
        # get former data? or do we just update the fields mentioned?
        data = {}
        Rule(api_root=api_root, auth0_secrets=auth0_secrets, rule_id=rule_id).update_rule(**data)

    def run(self, productName, version, build_number, rule_ids, backgroundRate=None):
        name = get_release_blob_name(productName, version, build_number, self.suffix)
        for rule_id in rule_ids:
            data = {"mapping": name}
            if backgroundRate:
                data["backgroundRate"] = backgroundRate


class ReleaseScheduler(object):
    def __init__(self, api_root, auth0_secrets=None, dummy=False, suffix=""):
        self.api_root = api_root
        self.auth0_secrets = auth0_secrets
        self.suffix = suffix
        if dummy:
            self.suffix = "-dummy"

    def run(self, productName, version, build_number, rule_ids, forceFallbackMappingUpdate=False, when=None, backgroundRate=None):
        name = get_release_blob_name(productName, version, build_number, self.suffix)

        if when is not None:
            when = arrow.get(when)

        soon = arrow.now().shift(minutes=5)
        if when is None or when < soon:
            when = soon

        for rule_id in rule_ids:
            data, data_version = Rule(api_root=self.api_root, auth0_secrets=self.auth0_secrets, rule_id=rule_id).get_data()
            # If the _currently_ shipped release is at a background rate of
            # 100%, it's safe to set it as the fallback mapping. (Everyone
            # was getting it anyways, so it's OK for them to fall back to
            # it if they don't get the even newer one.)
            # If it was _not_ shipped at 100%, we can't set it as the fallback.
            # If we did, it would mean users on the wrong side of the die roll
            # would either get the even newer release, or the release that
            # previously wasn't shipped to everyone - which we can't assume is
            # safe.
            # Alternatively, if we were specifically asked to update the fallback mapping, do it :)
            if data["backgroundRate"] == 100 or forceFallbackMappingUpdate:
                data["fallbackMapping"] = data["mapping"]
            data["mapping"] = name
            data["data_verison"] = data_version
            data["rule_id"] = rule_id
            data["change_type"] = "update"
            # We receive an iso8601 datetime, but what Balrog needs is a to-the-millisecond epoch timestamp
            data["when"] = when.int_timestamp * 1000
            if backgroundRate:
                data["backgroundRate"] = backgroundRate

            ScheduledRuleChange(api_root=self.api_root, auth0_secrets=self.auth0_secrets, rule_id=rule_id).add_scheduled_rule_change(**data)


class ReleaseStateUpdater(object):
    def __init__(self, api_root, auth0_secrets=None):
        self.api_root = api_root
        self.auth0_secrets = auth0_secrets

    def run(self, productName, version, build_number):
        name = get_release_blob_name(productName, version, build_number)
        ReleaseState(name, api_root=self.api_root, auth0_secrets=self.auth0_secrets).set_readonly()
