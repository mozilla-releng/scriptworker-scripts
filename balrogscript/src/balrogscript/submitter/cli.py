import json
import logging

import arrow
from balrogclient import Release, ReleaseState, Rule, ScheduledRuleChange, SingleLocale, balrog_request, get_balrog_session
from deepmerge import always_merger
from redo import retry
from requests.exceptions import HTTPError

from .release import buildbot2bouncer, buildbot2ftp, buildbot2updatePlatforms, getPrettyVersion, getProductDetails, makeCandidatesDir
from .util import recursive_update

log = logging.getLogger(__name__)


def get_nightly_blob_name(productName, branch, build_type, suffix, dummy=False):
    if dummy:
        branch = "%s-dummy" % branch
    return "%s-%s-%s-%s" % (productName, branch, build_type, suffix)


def get_release_blob_name(productName, version, build_number, suffix=None):
    if suffix is None:
        suffix = ""
    return "%s-%s-build%s%s" % (productName, version, build_number, suffix)


class ReleaseCreatorFileUrlsMixin(object):
    def _getFileUrls(self, productName, version, buildNumber, updateChannels, ftpServer, bouncerServer, partialUpdates, requiresMirrors=True):
        data = {"fileUrls": {}}
        file_prefix = productName.lower()
        if file_prefix == "devedition":
            file_prefix = "firefox"
        # bug 1444406 - eventually we're going to default to https
        protocol = "https"

        # "*" is for the default set of fileUrls, which generally points at
        # bouncer. It's helpful to have this to reduce duplication between
        # the live channel and the cdntest channel (which eliminates the
        # possibility that those two channels serve different contents).
        uniqueChannels = ["*"]
        for c in updateChannels:
            # localtest channels are different than the default because they
            # point directly at FTP rather than Bouncer.
            if "localtest" in c:
                uniqueChannels.append(c)
            # beta and beta-cdntest are special, but only if requiresMirrors is
            # set to False. This is typically used when generating beta channel
            # updates as part of RC builds, which get shipped prior to the
            # release being pushed to mirrors. This is a bit of a hack.
            if not requiresMirrors and c in ("beta", "beta-cdntest"):
                uniqueChannels.append(c)

        for channel in uniqueChannels:
            data["fileUrls"][channel] = {"completes": {}}
            if "localtest" in channel:
                dir_ = makeCandidatesDir(productName.lower(), version, buildNumber, server=ftpServer, protocol=protocol)
                filename = self.complete_mar_filename_pattern % (file_prefix, version)
                data["fileUrls"][channel]["completes"]["*"] = "%supdate/%%OS_FTP%%/%%LOCALE%%/%s" % (dir_, filename)
            else:
                # See comment above about these channels for explanation.
                if not requiresMirrors and channel in ("beta", "beta-cdntest"):
                    bouncerProduct = "%s-%sbuild%s-complete" % (productName.lower(), version, buildNumber)
                else:
                    if productName.lower() == "fennec":
                        bouncerProduct = "%s-%s" % (productName.lower(), version)
                    else:
                        bouncerProduct = self.complete_mar_bouncer_product_pattern % (productName.lower(), version)
                url = "%s://%s/?product=%s&os=%%OS_BOUNCER%%&lang=%%LOCALE%%" % (protocol, bouncerServer, bouncerProduct)
                data["fileUrls"][channel]["completes"]["*"] = url

        if not partialUpdates:
            return data

        for channel in uniqueChannels:
            data["fileUrls"][channel]["partials"] = {}
            for previousVersion, previousInfo in partialUpdates.items():
                from_ = get_release_blob_name(productName, previousVersion, previousInfo["buildNumber"], self.from_suffix)
                if "localtest" in channel:
                    dir_ = makeCandidatesDir(productName.lower(), version, buildNumber, server=ftpServer, protocol=protocol)
                    filename = "%s-%s-%s.partial.mar" % (file_prefix, previousVersion, version)
                    data["fileUrls"][channel]["partials"][from_] = "%supdate/%%OS_FTP%%/%%LOCALE%%/%s" % (dir_, filename)
                else:
                    # See comment above about these channels for explanation.
                    if not requiresMirrors and channel in ("beta", "beta-cdntest"):
                        bouncerProduct = "%s-%sbuild%s-partial-%sbuild%s" % (
                            productName.lower(),
                            version,
                            buildNumber,
                            previousVersion,
                            previousInfo["buildNumber"],
                        )
                    else:
                        bouncerProduct = "%s-%s-partial-%s" % (productName.lower(), version, previousVersion)
                    url = "%s://%s/?product=%s&os=%%OS_BOUNCER%%&lang=%%LOCALE%%" % (protocol, bouncerServer, bouncerProduct)
                    data["fileUrls"][channel]["partials"][from_] = url

        return data


class ReleaseCreatorV9(ReleaseCreatorFileUrlsMixin):
    schemaVersion = 9

    def __init__(
        self,
        api_root,
        auth0_secrets=None,
        dummy=False,
        suffix="",
        from_suffix="",
        complete_mar_filename_pattern=None,
        complete_mar_bouncer_product_pattern=None,
        backend_version=1,
    ):
        self.api_root = api_root
        self.auth0_secrets = auth0_secrets
        self.suffix = suffix
        self.from_suffix = from_suffix
        if dummy:
            self.suffix += "-dummy"
        self.complete_mar_filename_pattern = complete_mar_filename_pattern or "%s-%s.complete.mar"
        self.complete_mar_bouncer_product_pattern = complete_mar_bouncer_product_pattern or "%s-%s-complete"
        self.backend_version = backend_version

    def generate_data(self, appVersion, productName, version, buildNumber, updateChannels, ftpServer, bouncerServer, enUSPlatforms, updateLine, **updateKwargs):
        details_product = productName.lower()
        if details_product == "devedition":
            details_product = "firefox"
        if updateLine is None:
            updateLine = [{"for": {}, "fields": {"detailsURL": getProductDetails(details_product, appVersion), "type": "minor"}}]

        data = {"platforms": {}, "fileUrls": {}, "appVersion": appVersion, "displayVersion": getPrettyVersion(version), "updateLine": updateLine}

        fileUrls = self._getFileUrls(productName, version, buildNumber, updateChannels, ftpServer, bouncerServer, **updateKwargs)
        if fileUrls:
            data.update(fileUrls)

        for platform in enUSPlatforms:
            updatePlatforms = buildbot2updatePlatforms(platform)
            bouncerPlatform = buildbot2bouncer(platform)
            ftpPlatform = buildbot2ftp(platform)
            data["platforms"][updatePlatforms[0]] = {"OS_BOUNCER": bouncerPlatform, "OS_FTP": ftpPlatform}
            for aliasedPlatform in updatePlatforms[1:]:
                data["platforms"][aliasedPlatform] = {"alias": updatePlatforms[0]}

        return data

    def run(
        self, appVersion, productName, version, buildNumber, updateChannels, ftpServer, bouncerServer, enUSPlatforms, hashFunction, updateLine, **updateKwargs
    ):
        blob = self.generate_data(
            appVersion, productName, version, buildNumber, updateChannels, ftpServer, bouncerServer, enUSPlatforms, updateLine, **updateKwargs
        )
        name = get_release_blob_name(productName, version, buildNumber, self.suffix)

        if self.backend_version == 2:
            log.info("Using backend version 2...")
            url = self.api_root + "/v2/releases/" + name
            data = {"product": productName, "blob": {}}
            session = get_balrog_session(auth0_secrets=self.auth0_secrets)
            try:
                current_data = balrog_request(session, "get", url)
                if current_data:
                    data["blob"] = current_data["blob"]
                    data["old_data_versions"] = current_data["data_versions"]
            except HTTPError as e:
                if e.response.status_code != 404:
                    raise
            data["blob"] = always_merger.merge(data["blob"], blob)
            data["blob"]["schema_version"] = self.schemaVersion
            data["blob"]["hashFunction"] = hashFunction
            data["blob"]["name"] = name
            balrog_request(session, "put", url, json=data)
        else:
            log.info("Using legacy backend version...")
            api = Release(name=name, auth0_secrets=self.auth0_secrets, api_root=self.api_root)
            try:
                current_data, data_version = api.get_data()
            except HTTPError as e:
                if e.response.status_code == 404:
                    log.warning("Release blob doesn't exist, using empty data...")
                    current_data, data_version = {}, None
                else:
                    raise

            blob = recursive_update(current_data, blob)
            api.update_release(
                product=productName, hashFunction=hashFunction, releaseData=json.dumps(blob), schemaVersion=self.schemaVersion, data_version=data_version
            )


class NightlySubmitterBase(object):
    build_type = "nightly"

    def __init__(self, api_root, auth0_secrets=None, dummy=False, url_replacements=None, backend_version=1):
        self.api_root = api_root
        self.auth0_secrets = auth0_secrets
        self.dummy = dummy
        self.url_replacements = url_replacements
        self.backend_version = backend_version

    def _replace_canocical_url(self, url):
        if self.url_replacements:
            for string_from, string_to in self.url_replacements:
                if string_from in url:
                    new_url = url.replace(string_from, string_to)
                    log.warning("Replacing %s with %s", url, new_url)
                    return new_url

        return url

    def run(self, platform, buildID, productName, branch, appVersion, locale, hashFunction, extVersion, schemaVersion, isOSUpdate=None, **updateKwargs):
        if self.backend_version == 2:
            return self.run_backend2(
                platform, buildID, productName, branch, appVersion, locale, hashFunction, extVersion, schemaVersion, isOSUpdate=isOSUpdate, **updateKwargs
            )
        return self.run_backend1(
            platform, buildID, productName, branch, appVersion, locale, hashFunction, extVersion, schemaVersion, isOSUpdate=isOSUpdate, **updateKwargs
        )

    def run_backend1(
        self, platform, buildID, productName, branch, appVersion, locale, hashFunction, extVersion, schemaVersion, isOSUpdate=None, **updateKwargs
    ):
        assert schemaVersion in (3, 4), "Unhandled schema version %s" % schemaVersion
        log.info("Using legacy backend version...")
        targets = buildbot2updatePlatforms(platform)
        build_target = targets[0]
        alias = None
        if len(targets) > 1:
            alias = targets[1:]
        data = {"buildID": buildID, "appVersion": appVersion, "platformVersion": extVersion, "displayVersion": appVersion}
        if isOSUpdate:
            data["isOSUpdate"] = isOSUpdate

        data.update(self._get_update_data(productName, branch, **updateKwargs))

        if "old-id" in platform:
            # bug 1366034: support old-id builds
            # Like 1055305, this is a hack to support two builds with same build target that
            # require differed't release blobs and rules
            build_type = "old-id-%s" % self.build_type
        else:
            build_type = self.build_type

        name = get_nightly_blob_name(productName, branch, build_type, buildID, self.dummy)

        api = SingleLocale(name=name, build_target=build_target, locale=locale, auth0_secrets=self.auth0_secrets, api_root=self.api_root)

        # wrap operations into "atomic" functions that can be retried
        def update_dated():
            current_data, data_version = api.get_data()
            # If the  partials are already a subset of the blob and the
            # complete MAR is the same, skip the submission
            skip_submission = bool(
                current_data
                and current_data.get("completes") == data.get("completes")
                and all(p in current_data.get("partials", []) for p in data.get("partials", []))
            )
            if skip_submission:
                log.warning("Dated data didn't change, skipping update")
                return
            # explicitly pass data version
            api.update_build(
                product=productName,
                hashFunction=hashFunction,
                buildData=json.dumps(data),
                alias=json.dumps(alias),
                schemaVersion=schemaVersion,
                data_version=data_version,
            )

        # Most retries are caused by losing a data race. In these cases,
        # there's no point in waiting a long time to retry, so we reduce
        # sleeptime and increase the number of attempts instead.
        retry(update_dated, sleeptime=2, max_sleeptime=2, attempts=10)

        latest = SingleLocale(
            api_root=self.api_root,
            auth0_secrets=self.auth0_secrets,
            name=get_nightly_blob_name(productName, branch, build_type, "latest", self.dummy),
            build_target=build_target,
            locale=locale,
        )

        def update_latest():
            # copy everything over using target release's data version
            latest_data, latest_data_version = latest.get_data()
            source_data, _ = api.get_data()
            if source_data == latest_data:
                log.warning("Latest data didn't change, skipping update")
                return
            log.debug(f"Submitting latest update with data version {latest_data_version}")
            latest.update_build(
                product=productName,
                hashFunction=hashFunction,
                buildData=json.dumps(source_data),
                alias=json.dumps(alias),
                schemaVersion=schemaVersion,
                data_version=latest_data_version,
            )

        retry(update_latest, sleeptime=2, max_sleeptime=2, attempts=10)

    def run_backend2(
        self, platform, buildID, productName, branch, appVersion, locale, hashFunction, extVersion, schemaVersion, isOSUpdate=None, **updateKwargs
    ):
        log.info("Using backend version 2...")
        session = get_balrog_session(auth0_secrets=self.auth0_secrets)

        targets = buildbot2updatePlatforms(platform)
        build_target = targets[0]
        alias = None
        if len(targets) > 1:
            alias = targets[1:]
            log.debug("alias entry of %s ignored...", json.dumps(alias))
        data = {"buildID": buildID, "appVersion": appVersion, "platformVersion": extVersion, "displayVersion": appVersion}

        data.update(self._get_update_data(productName, branch, **updateKwargs))

        build_type = self.build_type

        # wrap operations into "atomic" functions that can be retried
        def update_data(url, existing_release, existing_locale_data):
            # If the  partials are already a subset of the blob and the
            # complete MAR is the same, skip the submission
            skip_submission = bool(
                existing_locale_data
                and existing_locale_data.get("completes") == data.get("completes")
                and all(p in existing_locale_data.get("partials", []) for p in data.get("partials", []))
            )
            if skip_submission:
                log.warning("Dated data didn't change, skipping update")
                return
            # explicitly pass data version
            new_data = {"blob": {"platforms": {build_target: {"locales": {locale: data}}}}, "old_data_versions": {"platforms": {build_target: {"locales": {}}}}}
            if existing_release.get("data_versions", {}).get("platforms", {}).get(build_target, {}).get("locales", {}).get(locale):
                new_data["old_data_versions"]["platforms"][build_target]["locales"][locale] = existing_release["data_versions"]["platforms"][build_target][
                    "locales"
                ][locale]
            balrog_request(session, "post", url, json=new_data)

        for identifier in (buildID, "latest"):
            name = get_nightly_blob_name(productName, branch, build_type, identifier, self.dummy)
            url = self.api_root + "/v2/releases/" + name
            try:
                existing_release = balrog_request(session, "get", url)
            except HTTPError as excp:
                if excp.response.status_code == 404:
                    log.info("No existing release %s, creating it...", name)
                    # TODO: we should also submit alias' here.
                    # not doing so will cause issues with dated blobs if we
                    # point rules at them
                    # in reality this isn't a problem 99% of the time so it's
                    # being ignored for new in favour of expediency
                    toplevel_data = {
                        "blob": {
                            "name": name,
                            "hashFunction": hashFunction,
                            "schema_version": 4,
                        },
                        "product": productName,
                    }
                    # In theory multiple requests can race against each other on this
                    # but since they're all submitting the same data they'll all get 200s
                    balrog_request(session, "put", url, json=toplevel_data)
                    existing_release = {"blob": {}}
                else:
                    raise
            existing_locale_data = existing_release["blob"].get(build_type, {}).get("locales", {}).get(locale)
            update_data(url, existing_release, existing_locale_data)


class MultipleUpdatesNightlyMixin(object):
    def _get_update_data(self, productName, branch, completeInfo=None, partialInfo=None):
        data = {}

        if completeInfo:
            data["completes"] = []
            for info in completeInfo:
                if "from_buildid" in info:
                    from_ = get_nightly_blob_name(productName, branch, self.build_type, info["from_buildid"], self.dummy)
                else:
                    from_ = "*"
                data["completes"].append(
                    {"from": from_, "filesize": info["size"], "hashValue": info["hash"], "fileUrl": self._replace_canocical_url(info["url"])}
                )
        if partialInfo:
            data["partials"] = []
            for info in partialInfo:
                data["partials"].append(
                    {
                        "from": get_nightly_blob_name(productName, branch, self.build_type, info["from_buildid"], self.dummy),
                        "filesize": info["size"],
                        "hashValue": info["hash"],
                        "fileUrl": self._replace_canocical_url(info["url"]),
                    }
                )

        return data


class NightlySubmitterV4(NightlySubmitterBase, MultipleUpdatesNightlyMixin):
    def run(self, *args, **kwargs):
        return NightlySubmitterBase.run(self, *args, schemaVersion=4, **kwargs)


class MultipleUpdatesReleaseMixin(object):
    def _get_update_data(self, productName, version, build_number, completeInfo=None, partialInfo=None):
        data = {}

        if completeInfo:
            data["completes"] = []
            for info in completeInfo:
                if "previousVersion" in info:
                    from_ = get_release_blob_name(productName, version, build_number, self.from_suffix)
                else:
                    from_ = "*"
                data["completes"].append({"from": from_, "filesize": info["size"], "hashValue": info["hash"]})
        if partialInfo:
            data["partials"] = []
            for info in partialInfo:
                data["partials"].append(
                    {
                        "from": get_release_blob_name(productName, info["previousVersion"], info["previousBuildNumber"], self.from_suffix),
                        "filesize": info["size"],
                        "hashValue": info["hash"],
                    }
                )

        return data


class ReleaseSubmitterV9(MultipleUpdatesReleaseMixin):
    def __init__(self, api_root, auth0_secrets=None, dummy=False, suffix="", from_suffix="", backend_version=1):
        self.api_root = api_root
        self.auth0_secrets = auth0_secrets
        self.suffix = suffix
        if dummy:
            self.suffix += "-dummy"
        self.from_suffix = from_suffix
        self.backend_version = backend_version

    def run(self, platform, productName, appVersion, version, build_number, locale, hashFunction, extVersion, buildID, **updateKwargs):
        targets = buildbot2updatePlatforms(platform)
        # Some platforms may have alias', but those are set-up elsewhere
        # for release blobs.
        build_target = targets[0]

        name = get_release_blob_name(productName, version, build_number, self.suffix)
        locale_data = {"buildID": buildID, "appVersion": appVersion, "displayVersion": getPrettyVersion(version)}

        locale_data.update(self._get_update_data(productName, version, build_number, **updateKwargs))

        if self.backend_version == 2:
            log.info("Using backend version 2...")
            # XXX Check for existing data_version for this locale
            data = {
                "blob": {"platforms": {build_target: {"locales": {locale: locale_data}}}},
                # XXX old_data_versions here is currently required but shouldn't be
                "old_data_versions": {"platforms": {build_target: {"locales": {}}}},
            }
            url = self.api_root + "/v2/releases/" + name
            session = get_balrog_session(auth0_secrets=self.auth0_secrets)
            balrog_request(session, "post", url, json=data)
        else:
            log.info("Using legacy backend version...")
            api = SingleLocale(name=name, build_target=build_target, locale=locale, auth0_secrets=self.auth0_secrets, api_root=self.api_root)
            current_data, data_version = api.get_data()
            api.update_build(data_version=data_version, product=productName, hashFunction=hashFunction, buildData=json.dumps(locale_data), schemaVersion=9)


class ReleasePusher(object):
    def __init__(self, api_root, auth0_secrets=None, dummy=False, suffix=""):
        self.api_root = api_root
        self.auth0_secrets = auth0_secrets
        self.suffix = suffix
        if dummy:
            self.suffix += "-dummy"

    def run(self, productName, version, build_number, rule_ids, backgroundRate=None):
        name = get_release_blob_name(productName, version, build_number, self.suffix)
        for rule_id in rule_ids:
            data = {"mapping": name}
            if backgroundRate:
                data["backgroundRate"] = backgroundRate
            Rule(api_root=self.api_root, auth0_secrets=self.auth0_secrets, rule_id=rule_id).update_rule(**data)


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
            data["when"] = when.timestamp * 1000
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
