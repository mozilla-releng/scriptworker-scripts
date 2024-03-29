import unittest
from unittest.mock import patch

from pushapkscript.publish import publish, publish_aab

from .helpers.mock_file import MockFile, mock_open


# TODO: refactor to pytest instead of unittest
@patch("pushapkscript.publish.open", new=mock_open)
@patch("pushapkscript.publish.push_apk")
@patch("pushapkscript.publish.push_aab")
class PublishTest(unittest.TestCase):
    def setUp(self):
        self.publish_config = {
            "target_store": "google",
            "dry_run": True,
            "google_track": "beta",
            "package_names": ["org.mozilla.fennec_aurora"],
            "secret": "/google_credentials.json",
        }
        self.apks = [MockFile("/path/to/x86.apk"), MockFile("/path/to/arm_v15.apk")]
        self.aabs = [MockFile("/path/to/aab1.aab"), MockFile("/path/to/aab2.aab")]

    def test_publish_config(self, mock_push_aab, mock_push_apk):
        publish({}, self.publish_config, self.apks, contact_server=True)

        mock_push_apk.assert_called_with(
            apks=[MockFile("/path/to/x86.apk"), MockFile("/path/to/arm_v15.apk")],
            secret="/google_credentials.json",
            track="beta",
            expected_package_names=["org.mozilla.fennec_aurora"],
            rollout_percentage=None,
            dry_run=True,
            contact_server=True,
            skip_check_multiple_locales=False,
            skip_check_ordered_version_codes=False,
            skip_check_same_locales=False,
            skip_checks_fennec=False,
        )

    def test_publish_aab_config(self, mock_push_aab, mock_push_apk):
        publish_aab({}, self.publish_config, self.aabs, contact_server=True)

        mock_push_aab.assert_called_with(
            aabs=[MockFile("/path/to/aab1.aab"), MockFile("/path/to/aab2.aab")],
            secret="/google_credentials.json",
            track="beta",
            rollout_percentage=None,
            dry_run=True,
            contact_server=True,
        )

    def test_publish_allows_rollout_percentage(self, mock_push_aab, mock_push_apk):
        publish_config = {
            "target_store": "google",
            "dry_run": True,
            "google_track": "production",
            "google_rollout_percentage": 10,
            "package_names": ["org.mozilla.fennec_aurora"],
            "secret": "/google_credentials.json",
        }
        publish({}, publish_config, self.apks, contact_server=True)
        _, args = mock_push_apk.call_args
        assert args["track"] == "production"
        assert args["rollout_percentage"] == 10

    def test_publish_aab_allows_rollout_percentage(self, mock_push_aab, mock_push_apk):
        publish_config = {
            "dry_run": True,
            "google_track": "production",
            "google_rollout_percentage": 10,
            "package_names": ["org.mozilla.fennec_aurora"],
            "secret": "/google_credentials.json",
        }
        publish_aab({}, publish_config, self.aabs, contact_server=True)
        _, args = mock_push_aab.call_args
        assert args["track"] == "production"
        assert args["rollout_percentage"] == 10

    def test_craft_push_config_allows_to_contact_google_play_or_not(self, mock_push_aab, mock_push_apk):
        publish({}, self.publish_config, self.apks, contact_server=True)
        _, args = mock_push_apk.call_args
        assert args["contact_server"] is True

        publish({}, self.publish_config, self.apks, False)
        _, args = mock_push_apk.call_args
        assert args["contact_server"] is False

    def test_craft_push_aab_config_allows_to_contact_google_play_or_not(self, mock_push_aab, mock_push_apk):
        publish_aab({}, self.publish_config, self.aabs, contact_server=True)
        _, args = mock_push_aab.call_args
        assert args["contact_server"] is True

        publish_aab({}, self.publish_config, self.aabs, False)
        _, args = mock_push_aab.call_args
        assert args["contact_server"] is False

    def test_craft_push_config_skip_checking_multiple_locales(self, mock_push_aab, mock_push_apk):
        product_config = {"skip_check_multiple_locales": True}
        publish(product_config, self.publish_config, self.apks, contact_server=True)
        _, args = mock_push_apk.call_args
        assert args["skip_check_multiple_locales"] is True

    def test_craft_push_config_skip_checking_same_locales(self, mock_push_aab, mock_push_apk):
        product_config = {"skip_check_same_locales": True}
        publish(product_config, self.publish_config, self.apks, contact_server=True)
        _, args = mock_push_apk.call_args
        assert args["skip_check_same_locales"] is True

    def test_craft_push_config_expect_package_names(self, mock_push_aab, mock_push_apk):
        publish_config = {
            "target_store": "google",
            "dry_run": True,
            "google_track": "beta",
            "package_names": ["org.mozilla.focus", "org.mozilla.klar"],
            "secret": "/google_credentials.json",
        }
        publish({}, publish_config, self.apks, contact_server=True)
        _, args = mock_push_apk.call_args
        assert args["expected_package_names"] == ["org.mozilla.focus", "org.mozilla.klar"]

    def test_craft_push_config_allows_committing_apks(self, mock_push_aab, mock_push_apk):
        publish_config = {
            "target_store": "google",
            "dry_run": False,
            "google_track": "beta",
            "package_names": ["org.mozilla.focus", "org.mozilla.klar"],
            "secret": "/google_credentials.json",
        }
        publish({}, publish_config, self.apks, contact_server=True)
        _, args = mock_push_apk.call_args
        assert args["dry_run"] is False

    def test_craft_push_aab_config_allows_committing_apks(self, mock_push_aab, mock_push_apk):
        publish_config = {
            "dry_run": False,
            "google_track": "beta",
            "package_names": ["org.mozilla.focus", "org.mozilla.klar"],
            "secret": "/google_credentials.json",
        }
        publish_aab({}, publish_config, self.aabs, contact_server=True)
        _, args = mock_push_aab.call_args
        assert args["dry_run"] is False
