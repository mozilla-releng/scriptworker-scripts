import logging

from mozapkpublisher.push_apk import push_apk

log = logging.getLogger(__name__)


def publish(product_config, publish_config, apk_files, contact_server):
    push_apk(
        apks=apk_files,
        target_store=publish_config['target_store'],
        username=publish_config['username'],
        secret=publish_config['secret'],
        expected_package_names=publish_config['package_names'],
        track=publish_config.get('google_track'),
        rollout_percentage=publish_config.get('google_rollout_percentage'),
        dry_run=publish_config['dry_run'],
        # Only allowed to connect to store server if the configuration of the pushapkscript
        # instance allows it
        contact_server=contact_server,
        skip_check_ordered_version_codes=bool(product_config.get('skip_check_ordered_version_codes')),
        skip_check_multiple_locales=bool(product_config.get('skip_check_multiple_locales')),
        skip_check_same_locales=bool(product_config.get('skip_check_same_locales')),
        skip_checks_fennec=bool(product_config.get('skip_checks_fennec')),
    )
