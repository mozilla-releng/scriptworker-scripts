from pushapkscript.publish_config import _should_do_dry_run, get_publish_config

AURORA_CONFIG = {
    "override_channel_model": "choose_google_app_with_scope",
    "apps": {
        "aurora": {
            "package_names": ["org.mozilla.fennec_aurora"],
            "default_track": "beta",
            "certificate_alias": "aurora",
            "credentials_file": "aurora.json",
        }
    },
}

FOCUS_CONFIG = {
    "override_channel_model": "single_google_app",
    "app": {
        "certificate_alias": "focus",
        "package_names": ["org.mozilla.focus"],
        "credentials_file": "focus.json",
    },
}

FENIX_CONFIG = {
    "apps": {
        "production": {
            "package_names": ["org.mozilla.fenix"],
            "certificate_alias": "fenix",
            "google": {"default_track": "internal", "credentials_file": "fenix.json"},
            "samsung": {"service_account_id": "123456", "access_token": "abcdef"},
        }
    }
}

ANY_STORE_CONFIG = {
    "apps": {
        "production": {
            "package_names": ["org.mozilla.flex"],
            "certificate_alias": "flex",
            "google": {"default_track": "internal", "credentials_file": "flex.json"},
        }
    }
}


def test_get_publish_config_fennec():
    assert get_publish_config(AURORA_CONFIG, {}, "aurora") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "aurora",
        "google_track": "beta",
        "rollout_percentage": None,
        "secret": "aurora.json",
        "package_names": ["org.mozilla.fennec_aurora"],
    }


def test_get_publish_config_fennec_track_override():
    assert get_publish_config(AURORA_CONFIG, {"google_play_track": "internal_qa"}, "aurora") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "aurora",
        "google_track": "internal_qa",
        "rollout_percentage": None,
        "secret": "aurora.json",
        "package_names": ["org.mozilla.fennec_aurora"],
    }


def test_get_publish_config_fennec_rollout():
    assert get_publish_config(AURORA_CONFIG, {"rollout_percentage": 10}, "aurora") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "aurora",
        "google_track": "beta",
        "rollout_percentage": 10,
        "secret": "aurora.json",
        "package_names": ["org.mozilla.fennec_aurora"],
    }


def test_get_publish_config_focus():
    payload = {"channel": "beta"}
    assert get_publish_config(FOCUS_CONFIG, payload, "focus") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "focus",
        "google_track": "beta",
        "rollout_percentage": None,
        "secret": "focus.json",
        "package_names": ["org.mozilla.focus"],
    }


def test_get_publish_config_focus_rollout():
    payload = {"channel": "production", "rollout_percentage": 10}
    assert get_publish_config(FOCUS_CONFIG, payload, "focus") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "focus",
        "google_track": "production",
        "rollout_percentage": 10,
        "secret": "focus.json",
        "package_names": ["org.mozilla.focus"],
    }


def test_get_publish_config_fenix():
    payload = {"channel": "production"}
    assert get_publish_config(FENIX_CONFIG, payload, "fenix") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "fenix",
        "google_track": "internal",
        "rollout_percentage": None,
        "secret": "fenix.json",
        "package_names": ["org.mozilla.fenix"],
    }


def test_get_publish_config_fenix_rollout():
    payload = {"channel": "production", "rollout_percentage": 10}
    assert get_publish_config(FENIX_CONFIG, payload, "fenix") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "fenix",
        "google_track": "internal",
        "rollout_percentage": 10,
        "secret": "fenix.json",
        "package_names": ["org.mozilla.fenix"],
    }


def test_target_google():
    payload = {"channel": "production", "target_store": "google"}
    assert get_publish_config(ANY_STORE_CONFIG, payload, "flex") == {
        "target_store": "google",
        "dry_run": True,
        "certificate_alias": "flex",
        "google_track": "internal",
        "rollout_percentage": None,
        "secret": "flex.json",
        "package_names": ["org.mozilla.flex"],
    }


def test_target_samsung():
    payload = {"channel": "production", "target_store": "samsung"}

    assert get_publish_config(FENIX_CONFIG, payload, "fenix") == {
        "target_store": "samsung",
        "dry_run": True,
        "sgs_service_account_id": "123456",
        "sgs_access_token": "abcdef",
        "package_names": ["org.mozilla.fenix"],
        "rollout_percentage": None,
        "submit": False,
    }


def test_target_samsung_with_commit():
    payload = {"channel": "production", "target_store": "samsung", "commit": True}

    assert get_publish_config(FENIX_CONFIG, payload, "fenix") == {
        "target_store": "samsung",
        "dry_run": False,
        "sgs_service_account_id": "123456",
        "sgs_access_token": "abcdef",
        "package_names": ["org.mozilla.fenix"],
        "rollout_percentage": None,
        "submit": False,
    }


def test_target_samsung_rollout():
    payload = {"channel": "production", "target_store": "samsung", "rollout_percentage": 50}

    assert get_publish_config(FENIX_CONFIG, payload, "fenix") == {
        "target_store": "samsung",
        "dry_run": True,
        "sgs_service_account_id": "123456",
        "sgs_access_token": "abcdef",
        "package_names": ["org.mozilla.fenix"],
        "rollout_percentage": 50,
        "submit": False,
    }


def test_target_samsung_submit():
    payload = {"channel": "production", "target_store": "samsung", "submit": True}

    assert get_publish_config(FENIX_CONFIG, payload, "fenix") == {
        "target_store": "samsung",
        "dry_run": True,
        "sgs_service_account_id": "123456",
        "sgs_access_token": "abcdef",
        "package_names": ["org.mozilla.fenix"],
        "rollout_percentage": None,
        "submit": True,
    }


def test_should_do_dry_run():
    task_payload = {"commit": True}
    assert _should_do_dry_run(task_payload) is False

    task_payload = {"commit": False}
    assert _should_do_dry_run(task_payload) is True

    task_payload = {}
    assert _should_do_dry_run(task_payload) is True
