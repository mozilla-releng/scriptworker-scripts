import logging

from mozapkpublisher.push_apk import push_apk

log = logging.getLogger(__name__)

_DEFAULT_TRACK_VALUES = ['production', 'beta', 'alpha', 'rollout', 'internal']


def publish_to_googleplay(payload, product_config, publish_config, apk_files, contact_google_play):
    with open(publish_config['google_credentials_file'], 'rb') as certificate:
        push_apk(
            apks=apk_files,
            service_account=publish_config['service_account'],
            google_play_credentials_file=certificate,
            track=publish_config['google_play_track'],
            expected_package_names=publish_config['package_names'],
            rollout_percentage=publish_config.get('rollout_percentage'),  # may be None
            commit=should_commit_transaction(payload),
            # Only allowed to connect to Google Play if the configuration of the pushapkscript instance allows it
            contact_google_play=contact_google_play,
            skip_check_ordered_version_codes=bool(product_config.get('skip_check_ordered_version_codes')),
            skip_check_multiple_locales=bool(product_config.get('skip_check_multiple_locales')),
            skip_check_same_locales=bool(product_config.get('skip_check_same_locales')),
            skip_checks_fennec=bool(product_config.get('skip_checks_fennec')),
        )


def should_commit_transaction(task_payload):
    # Don't commit anything by default. Committed APKs can't be unpublished,
    # unless you push a newer set of APKs.
    return task_payload.get('commit', False)
