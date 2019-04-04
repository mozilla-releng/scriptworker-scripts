import unittest
from balrogscript.submitter.cli import NightlySubmitterBase, NightlySubmitterV4
from balrogclient import SingleLocale
from mock import patch


class TestNightlySubmitterBase(unittest.TestCase):

    def test_replace_canocical_url(self):
        url_replacements = [
            ("ftp.mozilla.org", "download.cdn.mozilla.net")
        ]
        submitter = NightlySubmitterBase(api_root=None, auth0_secrets=None,
                                         url_replacements=url_replacements)
        self.assertEqual(
            'http://download.cdn.mozilla.net/pub/mozilla.org/some/file',
            submitter._replace_canocical_url(
                'http://ftp.mozilla.org/pub/mozilla.org/some/file')
        )


class TestNightlySubmitterV4(unittest.TestCase):

    def test_canonical_ur_replacement(self):
        url_replacements = [
            ("ftp.mozilla.org", "download.cdn.mozilla.net")
        ]
        submitter = NightlySubmitterV4(api_root=None, auth0_secrets=None,
                                       url_replacements=url_replacements)
        completeInfo = [{
            'size': 123,
            'hash': 'abcd',
            'url': 'http://ftp.mozilla.org/url'
        }]
        data = submitter._get_update_data("prod", "brnch", completeInfo)
        self.assertDictEqual(
            data,
            {'completes': [{
                'fileUrl': 'http://download.cdn.mozilla.net/url',
                'filesize': 123,
                'from': '*',
                'hashValue': 'abcd'
            }]})

    def test_no_canonical_ur_replacement(self):
        submitter = NightlySubmitterV4(api_root=None, auth0_secrets=None,
                                       url_replacements=None)
        completeInfo = [{
            'size': 123,
            'hash': 'abcd',
            'url': 'http://ftp.mozilla.org/url'
        }]
        data = submitter._get_update_data("prod", "brnch", completeInfo)
        self.assertDictEqual(
            data,
            {'completes': [{
                'fileUrl': 'http://ftp.mozilla.org/url',
                'filesize': 123,
                'from': '*',
                'hashValue': 'abcd'
            }]})


class TestUpdateIdempotency(unittest.TestCase):

    @patch.object(SingleLocale, 'update_build')
    @patch.object(SingleLocale, 'get_data')
    def test_new_data(self, get_data, update_build):
        """SingleLocale.update_build() should be called twice when new data
        submitted"""
        get_data.side_effect = [
            # first call, the dated blob, assume there is no data yet
            ({}, None),
            # second call, get the "latest" blob's data
            ({}, 100),
            # Third call, get data from the dated blob
            ({"buildID": "b1", "appVersion": "a1", "displayVersion": "a1",
              "partials": [{"fileUrl": "p_url1", "from": "pr1-b1-nightly-b0",
                            "hashValue": "p_hash1", "filesize": 1}],
              "platformVersion": "v1",
              "completes": [{"fileUrl": "c_url1", "hashValue": "c_hash1",
                             "from": "*", "filesize": 2}]}, 1)
        ]
        partial_info = [{
            "url": "p_url1",
            "hash": "p_hash1",
            "size": 1,
            "from_buildid": "b0"
        }]
        complete_info = [{
            "url": "c_url1",
            "hash": "c_hash1",
            "size": 2,
        }]
        submitter = NightlySubmitterV4("api_root", auth0_secrets=None)
        submitter.run(platform="linux64", buildID="b1", productName="pr1",
                      branch="b1", appVersion="a1", locale="l1",
                      hashFunction='sha512', extVersion="v1",
                      partialInfo=partial_info, completeInfo=complete_info)
        self.assertEqual(update_build.call_count, 2)

    @patch.object(SingleLocale, 'update_build')
    @patch.object(SingleLocale, 'get_data')
    def test_same_dated_data(self, get_data, update_build):
        partials = [
            {
                "from": "pr1-b1-nightly-b0", "filesize": 1,
                "hashValue": "p_hash1", "fileUrl": "p_url1"
            },
            {
                "from": "pr1-b1-nightly-b1000", "filesize": 1000,
                "hashValue": "p_hash1000", "fileUrl": "p_url1000"
            },
        ]
        completes = [{
            "from": "*", "filesize": 2, "hashValue": "c_hash1",
            "fileUrl": "c_url1"
        }]
        partial_info = [{
            "url": "p_url1",
            "hash": "p_hash1",
            "size": 1,
            "from_buildid": "b0"
        }]
        complete_info = [{
            "url": "c_url1",
            "hash": "c_hash1",
            "size": 2,
            "from": "*"
        }]
        data = {"buildID": "b1", "appVersion": "a1", "displayVersion": "a1",
                "platformVersion": "v1",
                "partials": partials, "completes": completes}
        get_data.side_effect = [
            # first call, the dated blob, assume it contains the same data
            (data, 1),
            # second call, get the "latest" blob's data version, data itself is
            # not important and discarded
            ({}, 100),
            # Third call, get data from the dated blob
            (data, 1)]

        submitter = NightlySubmitterV4("api_root", auth0_secrets=None)
        submitter.run(platform="linux64", buildID="b1", productName="pr1",
                      branch="b1", appVersion="a1", locale="l1",
                      hashFunction='sha512', extVersion="v1",
                      partialInfo=partial_info, completeInfo=complete_info)
        self.assertEqual(update_build.call_count, 1)

    @patch.object(SingleLocale, 'update_build')
    @patch.object(SingleLocale, 'get_data')
    def test_same_latest_data(self, get_data, update_build):
        partials = [{
            "from": "pr1-b1-nightly-b0", "filesize": 1, "hashValue": "p_hash1",
            "fileUrl": "p_url1"
        }]
        completes = [{
            "from": "*", "filesize": 2, "hashValue": "c_hash1",
            "fileUrl": "c_url1"
        }]
        partial_info = [{
            "url": "p_url1",
            "hash": "p_hash1",
            "size": 1,
            "from_buildid": "b0"
        }]
        complete_info = [{
            "url": "c_url1",
            "hash": "c_hash1",
            "size": 2,
            "from": "*"
        }]
        data = {"buildID": "b1", "appVersion": "a1", "displayVersion": "a1",
                "platformVersion": "v1",
                "partials": partials, "completes": completes}
        get_data.side_effect = [
            # first call, the dated blob, assume it contains the same data
            (data, 1),
            # second call, get the "latest" blob's data version, data itself is
            # not important and discarded
            (data, 100),
            # Third call, get data from the dated blob
            (data, 1)]

        submitter = NightlySubmitterV4("api_root", auth0_secrets=None)
        submitter.run(platform="linux64", buildID="b1", productName="pr1",
                      branch="b1", appVersion="a1", locale="l1",
                      hashFunction='sha512', extVersion="v1",
                      partialInfo=partial_info, completeInfo=complete_info)
        self.assertEqual(update_build.call_count, 0)
