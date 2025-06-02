import logging

from mozapkpublisher.push_aab import push_aab
from mozapkpublisher.push_apk import push_apk

log = logging.getLogger(__name__)


async def publish(product_config, publish_config, apk_files, contact_server):
    if apk_files:
        await push_apk(
            apks=apk_files,
            secret=publish_config.get("secret"),
            expected_package_names=publish_config["package_names"],
            track=publish_config.get("google_track"),
            rollout_percentage=publish_config.get("rollout_percentage"),
            dry_run=publish_config["dry_run"],
            store=publish_config.get("target_store", "google"),
            # Only allowed to connect to store server if the configuration of the pushapkscript
            # instance allows it
            contact_server=contact_server,
            skip_check_ordered_version_codes=bool(product_config.get("skip_check_ordered_version_codes")),
            skip_check_multiple_locales=bool(product_config.get("skip_check_multiple_locales")),
            skip_check_same_locales=bool(product_config.get("skip_check_same_locales")),
            skip_checks_fennec=bool(product_config.get("skip_checks_fennec")),
            sgs_service_account_id=publish_config.get("sgs_service_account_id"),
            sgs_access_token=publish_config.get("sgs_access_token"),
        )


async def publish_aab(product_config, publish_config, aab_files, contact_server):
    if aab_files:
        await push_aab(
            aabs=aab_files,
            secret=publish_config.get("secret"),
            track=publish_config.get("google_track"),
            rollout_percentage=publish_config.get("rollout_percentage"),
            dry_run=publish_config["dry_run"],
            # Only allowed to connect to store server if the configuration of the pushapkscript
            # instance allows it
            contact_server=contact_server,
        )
