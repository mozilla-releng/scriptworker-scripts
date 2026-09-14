import requests
import tempfile

from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

from mozapkpublisher.common.utils import load_json_url, file_sha512sum, metadata_by_package_name

apk_x86 = NamedTemporaryFile()
apk_arm = NamedTemporaryFile()


def test_load_json_url(monkeypatch):
    response_mock = MagicMock()
    response_mock.json = MagicMock()
    monkeypatch.setattr(requests, 'get', lambda url: response_mock)
    load_json_url('https://dummy-url.tld')
    response_mock.json.assert_called_once_with()


def test_file_sha512sum():
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(b'known sha512')
        temp_file.seek(0)

        assert file_sha512sum(temp_file.name) == '0b1622c08ae1fcffe9f0d1dd17fe273d7e8c96668981c8a38f6bbfa4f757b30af0\
ed2aabf90f1f8a5983082a0b88194fe81bc850d3019fd9eca9328584227c84'


def test_metadata_by_package_name():
    one_package_apks_metadata = {
        apk_arm: {'package_name': 'org.mozilla.firefox'},
        apk_x86: {'package_name': 'org.mozilla.firefox'}
    }

    expected_one_package_metadata = {
        'org.mozilla.firefox': [
            (apk_arm, {'package_name': 'org.mozilla.firefox'}),
            (apk_x86, {'package_name': 'org.mozilla.firefox'}),
        ]
    }

    one_package_metadata = metadata_by_package_name(one_package_apks_metadata)
    assert len(one_package_metadata.keys()) == 1
    assert expected_one_package_metadata == one_package_metadata

    apk_arm_other = NamedTemporaryFile()
    two_package_apks_metadata = {
        apk_arm: {'package_name': 'org.mozilla.focus'},
        apk_x86: {'package_name': 'org.mozilla.focus'},
        apk_arm_other: {'package_name': 'org.mozilla.klar'}
    }

    expected_two_package_metadata = {
        'org.mozilla.klar': [
            (apk_arm_other, {'package_name': 'org.mozilla.klar'}),
        ],
        'org.mozilla.focus': [
            (apk_arm, {'package_name': 'org.mozilla.focus'}),
            (apk_x86, {'package_name': 'org.mozilla.focus'}),
        ]
    }

    two_package_metadata = metadata_by_package_name(two_package_apks_metadata)
    assert len(two_package_metadata.keys()) == 2
    assert expected_two_package_metadata == two_package_metadata
