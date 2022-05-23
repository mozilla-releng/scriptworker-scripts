import unittest

from balrogclient import SingleLocale
from mock import patch

from balrogscript.submitter.cli import NightlySubmitterBase, NightlySubmitterV4, PinnableVersion, ReleaseCreatorV9


class TestNightlySubmitterBase(unittest.TestCase):
    def test_replace_canocical_url(self):
        url_replacements = [("ftp.mozilla.org", "download.cdn.mozilla.net")]
        submitter = NightlySubmitterBase(api_root=None, auth0_secrets=None, url_replacements=url_replacements)
        self.assertEqual(
            "http://download.cdn.mozilla.net/pub/mozilla.org/some/file", submitter._replace_canocical_url("http://ftp.mozilla.org/pub/mozilla.org/some/file")
        )


class TestNightlySubmitterV4(unittest.TestCase):
    def test_canonical_ur_replacement(self):
        url_replacements = [("ftp.mozilla.org", "download.cdn.mozilla.net")]
        submitter = NightlySubmitterV4(api_root=None, auth0_secrets=None, url_replacements=url_replacements)
        completeInfo = [{"size": 123, "hash": "abcd", "url": "http://ftp.mozilla.org/url"}]
        data = submitter._get_update_data("prod", "brnch", completeInfo)
        self.assertDictEqual(data, {"completes": [{"fileUrl": "http://download.cdn.mozilla.net/url", "filesize": 123, "from": "*", "hashValue": "abcd"}]})

    def test_no_canonical_ur_replacement(self):
        submitter = NightlySubmitterV4(api_root=None, auth0_secrets=None, url_replacements=None)
        completeInfo = [{"size": 123, "hash": "abcd", "url": "http://ftp.mozilla.org/url"}]
        data = submitter._get_update_data("prod", "brnch", completeInfo)
        self.assertDictEqual(data, {"completes": [{"fileUrl": "http://ftp.mozilla.org/url", "filesize": 123, "from": "*", "hashValue": "abcd"}]})


class TestUpdateIdempotency(unittest.TestCase):
    @patch.object(SingleLocale, "update_build")
    @patch.object(SingleLocale, "get_data")
    def test_new_data(self, get_data, update_build):
        """SingleLocale.update_build() should be called twice when new data
        submitted"""
        get_data.side_effect = [
            # first call, the dated blob, assume there is no data yet
            ({}, None),
            # second call, get the "latest" blob's data
            ({}, 100),
            # Third call, get data from the dated blob
            (
                {
                    "buildID": "b1",
                    "appVersion": "a1",
                    "displayVersion": "a1",
                    "partials": [{"fileUrl": "p_url1", "from": "pr1-b1-nightly-b0", "hashValue": "p_hash1", "filesize": 1}],
                    "platformVersion": "v1",
                    "completes": [{"fileUrl": "c_url1", "hashValue": "c_hash1", "from": "*", "filesize": 2}],
                },
                1,
            ),
        ]
        partial_info = [{"url": "p_url1", "hash": "p_hash1", "size": 1, "from_buildid": "b0"}]
        complete_info = [{"url": "c_url1", "hash": "c_hash1", "size": 2}]
        submitter = NightlySubmitterV4("api_root", auth0_secrets=None)
        submitter.run(
            platform="linux64",
            buildID="b1",
            productName="pr1",
            branch="b1",
            appVersion="a1",
            locale="l1",
            hashFunction="sha512",
            extVersion="v1",
            partialInfo=partial_info,
            completeInfo=complete_info,
        )
        self.assertEqual(update_build.call_count, 2)

    @patch.object(SingleLocale, "update_build")
    @patch.object(SingleLocale, "get_data")
    def test_same_dated_data(self, get_data, update_build):
        partials = [
            {"from": "pr1-b1-nightly-b0", "filesize": 1, "hashValue": "p_hash1", "fileUrl": "p_url1"},
            {"from": "pr1-b1-nightly-b1000", "filesize": 1000, "hashValue": "p_hash1000", "fileUrl": "p_url1000"},
        ]
        completes = [{"from": "*", "filesize": 2, "hashValue": "c_hash1", "fileUrl": "c_url1"}]
        partial_info = [{"url": "p_url1", "hash": "p_hash1", "size": 1, "from_buildid": "b0"}]
        complete_info = [{"url": "c_url1", "hash": "c_hash1", "size": 2, "from": "*"}]
        data = {"buildID": "b1", "appVersion": "a1", "displayVersion": "a1", "platformVersion": "v1", "partials": partials, "completes": completes}
        get_data.side_effect = [
            # first call, the dated blob, assume it contains the same data
            (data, 1),
            # second call, get the "latest" blob's data version, data itself is
            # not important and discarded
            ({}, 100),
            # Third call, get data from the dated blob
            (data, 1),
        ]

        submitter = NightlySubmitterV4("api_root", auth0_secrets=None)
        submitter.run(
            platform="linux64",
            buildID="b1",
            productName="pr1",
            branch="b1",
            appVersion="a1",
            locale="l1",
            hashFunction="sha512",
            extVersion="v1",
            partialInfo=partial_info,
            completeInfo=complete_info,
        )
        self.assertEqual(update_build.call_count, 1)

    @patch.object(SingleLocale, "update_build")
    @patch.object(SingleLocale, "get_data")
    def test_same_latest_data(self, get_data, update_build):
        partials = [{"from": "pr1-b1-nightly-b0", "filesize": 1, "hashValue": "p_hash1", "fileUrl": "p_url1"}]
        completes = [{"from": "*", "filesize": 2, "hashValue": "c_hash1", "fileUrl": "c_url1"}]
        partial_info = [{"url": "p_url1", "hash": "p_hash1", "size": 1, "from_buildid": "b0"}]
        complete_info = [{"url": "c_url1", "hash": "c_hash1", "size": 2, "from": "*"}]
        data = {"buildID": "b1", "appVersion": "a1", "displayVersion": "a1", "platformVersion": "v1", "partials": partials, "completes": completes}
        get_data.side_effect = [
            # first call, the dated blob, assume it contains the same data
            (data, 1),
            # second call, get the "latest" blob's data version, data itself is
            # not important and discarded
            (data, 100),
            # Third call, get data from the dated blob
            (data, 1),
        ]

        submitter = NightlySubmitterV4("api_root", auth0_secrets=None)
        submitter.run(
            platform="linux64",
            buildID="b1",
            productName="pr1",
            branch="b1",
            appVersion="a1",
            locale="l1",
            hashFunction="sha512",
            extVersion="v1",
            partialInfo=partial_info,
            completeInfo=complete_info,
        )
        self.assertEqual(update_build.call_count, 0)


class TestReleaseCreatorFileUrlsMixin(unittest.TestCase):
    maxDiff = None

    def test_http_default(self):
        submitter = ReleaseCreatorV9(api_root=None, auth0_secrets=None)
        data = submitter._getFileUrls(
            "Firefox", "1.0", 1, ["release-localtest", "release-cdntest", "release"], "ftp.example.org", "download.example.org", {"0.5": {"buildNumber": 2}}
        )
        expected = {
            "fileUrls": {
                "*": {
                    "completes": {"*": "https://download.example.org/?product=firefox-1.0-complete&os=%OS_BOUNCER%&lang=%LOCALE%"},
                    "partials": {"Firefox-0.5-build2": "https://download.example.org/?product=firefox-1.0-partial-0.5&os=%OS_BOUNCER%&lang=%LOCALE%"},
                },
                "release-localtest": {
                    "completes": {
                        "*": "https://ftp.example.org/pub/firefox/candidates/1.0-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-1.0.complete.mar"
                    },
                    "partials": {
                        "Firefox-0.5-build2": "https://ftp.example.org/pub/firefox/candidates/1.0-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-0.5-1.0.partial.mar"  # noqa: E501
                    },
                },
            }
        }
        self.assertDictEqual(data, expected)

    def test_https_devedition(self):
        submitter = ReleaseCreatorV9(api_root=None, auth0_secrets=None)
        data = submitter._getFileUrls(
            "Devedition", "1.0", 1, ["aurora-localtest", "aurora-cdntest", "aurora"], "ftp.example.org", "download.example.org", {"0.5": {"buildNumber": 2}}
        )
        expected = {
            "fileUrls": {
                "*": {
                    "completes": {"*": "https://download.example.org/?product=devedition-1.0-complete&os=%OS_BOUNCER%&lang=%LOCALE%"},
                    "partials": {"Devedition-0.5-build2": "https://download.example.org/?product=devedition-1.0-partial-0.5&os=%OS_BOUNCER%&lang=%LOCALE%"},
                },
                "aurora-localtest": {
                    "completes": {
                        "*": "https://ftp.example.org/pub/devedition/candidates/1.0-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-1.0.complete.mar"
                    },
                    "partials": {
                        "Devedition-0.5-build2": "https://ftp.example.org/pub/devedition/candidates/1.0-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-0.5-1.0.partial.mar"  # noqa: E501
                    },
                },
            }
        }
        self.assertDictEqual(data, expected)

    def test_https_beta(self):
        submitter = ReleaseCreatorV9(api_root=None, auth0_secrets=None)
        data = submitter._getFileUrls(
            "Firefox", "1.0b1", 1, ["beta-localtest", "beta-cdntest", "beta"], "ftp.example.org", "download.example.org", {"0.5b1": {"buildNumber": 2}}
        )
        expected = {
            "fileUrls": {
                "*": {
                    "completes": {"*": "https://download.example.org/?product=firefox-1.0b1-complete&os=%OS_BOUNCER%&lang=%LOCALE%"},
                    "partials": {"Firefox-0.5b1-build2": "https://download.example.org/?product=firefox-1.0b1-partial-0.5b1&os=%OS_BOUNCER%&lang=%LOCALE%"},
                },
                "beta-localtest": {
                    "completes": {
                        "*": "https://ftp.example.org/pub/firefox/candidates/1.0b1-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-1.0b1.complete.mar"
                    },
                    "partials": {
                        "Firefox-0.5b1-build2": "https://ftp.example.org/pub/firefox/candidates/1.0b1-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-0.5b1-1.0b1.partial.mar"  # noqa: E501
                    },
                },
            }
        }
        self.assertDictEqual(data, expected)

    def test_https_RC_on_beta(self):
        submitter = ReleaseCreatorV9(api_root=None, auth0_secrets=None)
        data = submitter._getFileUrls(
            "Firefox", "1.0", 1, ["beta-localtest", "beta-cdntest", "beta"], "ftp.example.org", "download.example.org", {"1.0b1": {"buildNumber": 2}}, False
        )
        expected = {
            "fileUrls": {
                "*": {
                    "completes": {"*": "https://download.example.org/?product=firefox-1.0-complete&os=%OS_BOUNCER%&lang=%LOCALE%"},
                    "partials": {"Firefox-1.0b1-build2": "https://download.example.org/?product=firefox-1.0-partial-1.0b1&os=%OS_BOUNCER%&lang=%LOCALE%"},
                },
                "beta": {
                    "completes": {"*": "https://download.example.org/?product=firefox-1.0build1-complete&os=%OS_BOUNCER%&lang=%LOCALE%"},
                    "partials": {
                        "Firefox-1.0b1-build2": "https://download.example.org/?product=firefox-1.0build1-partial-1.0b1build2&os=%OS_BOUNCER%&lang=%LOCALE%"
                    },
                },
                "beta-cdntest": {
                    "completes": {"*": "https://download.example.org/?product=firefox-1.0build1-complete&os=%OS_BOUNCER%&lang=%LOCALE%"},
                    "partials": {
                        "Firefox-1.0b1-build2": "https://download.example.org/?product=firefox-1.0build1-partial-1.0b1build2&os=%OS_BOUNCER%&lang=%LOCALE%"
                    },
                },
                "beta-localtest": {
                    "completes": {
                        "*": "https://ftp.example.org/pub/firefox/candidates/1.0-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-1.0.complete.mar"
                    },
                    "partials": {
                        "Firefox-1.0b1-build2": "https://ftp.example.org/pub/firefox/candidates/1.0-candidates/build1/update/%OS_FTP%/%LOCALE%/firefox-1.0b1-1.0.partial.mar"  # noqa: E501
                    },
                },
            }
        }
        self.assertDictEqual(data, expected)


class TestPinnable(unittest.TestCase):
    def parse_pinnable_string(self, version_string, major_pin, minor_pin):
        pin_version = PinnableVersion(version_string)
        self.assertEqual(pin_version.major_pin(), major_pin)
        self.assertEqual(pin_version.minor_pin(), minor_pin)

    def test_pinnable_parsing(self):
        self.parse_pinnable_string("1.0", "1.", "1.0.")
        self.parse_pinnable_string("100.0", "100.", "100.0.")
        self.parse_pinnable_string("100.1", "100.", "100.1.")
        self.parse_pinnable_string("100.100", "100.", "100.100.")
        self.parse_pinnable_string("100.100.0", "100.", "100.100.")
        self.parse_pinnable_string("100.100.100", "100.", "100.100.")
        self.parse_pinnable_string("100.100a1", "100.", "100.100.")
        self.parse_pinnable_string("100.100b1", "100.", "100.100.")
        self.parse_pinnable_string("100.100.100a1", "100.", "100.100.")
        self.parse_pinnable_string("100.100.100b1", "100.", "100.100.")
