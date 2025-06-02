import logging

log = logging.getLogger(__name__)


def _should_do_dry_run(task):
    # Don't commit anything by default. Committed APKs can't be unpublished,
    # unless you push a newer set of APKs.
    return not task.get("commit", False)


def _handle_legacy_google_track(google_track):
    if google_track == "rollout":
        log.warn(
            'Using "rollout" as the Google Play Track is deprecated, please specify the '
            "target track that you would like to rollout to, instead. Assuming you meant "
            '"production" for this task.'
        )
        return "production"
    return google_track


def _get_single_google_app_publish_config(product_config, task):
    publish_config = product_config["app"]
    rollout_percentage = task.get("rollout_percentage")
    google_track = task["channel"]
    google_track = _handle_legacy_google_track(google_track)
    return {
        "target_store": "google",
        "dry_run": _should_do_dry_run(task),
        "certificate_alias": publish_config.get("certificate_alias"),
        "secret": publish_config["credentials_file"],
        "package_names": publish_config["package_names"],
        "google_track": google_track,
        "rollout_percentage": rollout_percentage,
    }


def _get_google_app_by_scope_publish_config(product_config, task, scope_product):
    publish_config = product_config["apps"][scope_product]
    rollout_percentage = task.get("rollout_percentage")
    google_track = task.get("google_play_track", publish_config["default_track"])
    google_track = _handle_legacy_google_track(google_track)
    return {
        "target_store": "google",
        "dry_run": _should_do_dry_run(task),
        "certificate_alias": publish_config.get("certificate_alias"),
        "secret": publish_config["credentials_file"],
        "package_names": publish_config["package_names"],
        "google_track": google_track,
        "rollout_percentage": rollout_percentage,
    }


def _get_channel_publish_config(product_config, task):
    publish_config = product_config["apps"][task["channel"]]
    target_store = task.get("target_store")

    # Determine the target store. If "target_store" isn't provided on the task payload,
    # attempt to automatically determine it by checking if the channel only supports a single
    # target - if so, then use that target store.
    if target_store:
        if not publish_config.get(target_store):
            raise ValueError('Task had `target_store` set to "{}", but the "{}" channel does not support that target'.format(target_store, task["channel"]))
    elif publish_config.get("google"):
        target_store = "google"
    else:
        raise ValueError("Unknown target store")

    store_config = publish_config[target_store]
    rollout_percentage = task.get("rollout_percentage")

    if target_store == "samsung":
        if task.get("google_play_track"):
            raise ValueError("`google_play_track` is not allowed on the task if the target store is samsung")

        return {
            "target_store": target_store,
            "dry_run": _should_do_dry_run(task),
            "package_names": publish_config["package_names"],
            "rollout_percentage": rollout_percentage,
            "sgs_service_account_id": store_config["service_account_id"],
            "sgs_access_token": store_config["access_token"],
        }

    google_track = task.get("google_play_track", store_config["default_track"])
    google_track = _handle_legacy_google_track(google_track)

    return {
        "target_store": target_store,
        "dry_run": _should_do_dry_run(task),
        "certificate_alias": publish_config.get("certificate_alias"),
        "secret": store_config["credentials_file"],
        "package_names": publish_config["package_names"],
        "google_track": google_track,
        "rollout_percentage": rollout_percentage,
    }


def get_publish_config(product_config, task, scope_product):
    override_channel_model = product_config.get("override_channel_model")
    if override_channel_model == "single_google_app":
        # reference-browser uses a single Google app - with `channel` refering to the google default track -
        # rather than a separate app-per-channel. So, reference-browser is configured with "single_google_app"
        return _get_single_google_app_publish_config(product_config, task)

    elif override_channel_model == "choose_google_app_with_scope":
        # Fennec only targets google, but doesn't provide the channel in the payload. We need
        # to leverage the legacy strategy of inferring the channel from the scope, then choosing
        # the Google app accordingly
        return _get_google_app_by_scope_publish_config(product_config, task, scope_product)

    else:
        # The common configuration will have "channel" specified in the payload, which is used
        # to choose the app to deploy to.
        return _get_channel_publish_config(product_config, task)
