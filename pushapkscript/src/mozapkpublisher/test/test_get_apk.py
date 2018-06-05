import mock
import os
import pytest
import shutil
from tempfile import mkdtemp

from mozapkpublisher.common.exceptions import CheckSumMismatch, WrongArgumentGiven
from mozapkpublisher.get_apk import GetAPK, \
    craft_apk_and_checksums_url_and_download_locations, _craft_apk_and_checksums_file_names, _get_architecture_in_file_name, \
    check_apk_against_checksum_file, _fetch_checksum_from_file, _take_out_common_path

VALID_CONFIG = {'version': '50.0b8'}
get_apk = GetAPK(VALID_CONFIG)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CHECKSUM_APK = os.path.join(DATA_DIR, 'blob')


def test_mutually_exclusive_group():
    with pytest.raises(WrongArgumentGiven):
        GetAPK({'clean': True, 'version': True})

    with pytest.raises(WrongArgumentGiven):
        GetAPK({'clean': True, 'latest_nightly': True})

    with pytest.raises(WrongArgumentGiven):
        GetAPK({'version': True, 'latest_nightly': True})


def test_generate_apk_base_url():
    assert GetAPK({'latest_nightly': True}).generate_apk_base_url('52.0a1', None, 'multi', 'x86') == \
        'https://ftp.mozilla.org/pub/mobile/nightly/latest-mozilla-central-android-x86'

    assert GetAPK({'version': '50.0b8'}).generate_apk_base_url('50.0b8', 1, 'multi', 'api-15') == \
        'https://ftp.mozilla.org/pub/mobile/candidates/50.0b8-candidates/build1/android-api-15/multi'


@pytest.mark.parametrize('version, architure, expected', ((
    '45.0', 'arm', ['api-9', 'api-11'],
), (
    '47.0', 'arm', ['api-9', 'api-15'],
), (
    '55.0', 'arm', ['api-15'],
), (
    '55.0', 'x86', ['x86'],
), (
    '56.0', 'arm', ['api-16'],
)))
def test_get_api_suffix(version, architure, expected):
    assert get_apk.get_api_suffix(version, architure) == expected


def test_craft_apk_and_checksums_url_and_download_locations():
    assert craft_apk_and_checksums_url_and_download_locations(
        'https://ftp.mozilla.org/pub/mobile/candidates/52.0b1-candidates/build1/android-api-15/multi',
        '/a/fake/download/directory', '52.0b1', 1, 'multi', 'arm'
    ) == {
        'apk': {
            'url': 'https://ftp.mozilla.org/pub/mobile/candidates/52.0b1-candidates/build1/android-api-15/multi/fennec-52.0b1.multi.android-arm.apk',
            'download_location': '/a/fake/download/directory/fennec-52.0b1.multi.android-arm.apk',
        },
        'checksums': {
            'url': 'https://ftp.mozilla.org/pub/mobile/candidates/52.0b1-candidates/build1/android-api-15/multi/fennec-52.0b1.multi.android-arm.checksums',
            'download_location': '/a/fake/download/directory/fennec-52.0b1.multi.android-arm.checksums',
        },
    }
    assert craft_apk_and_checksums_url_and_download_locations(
        'https://ftp.mozilla.org/pub/mobile/nightly/latest-mozilla-central-android-api-15',
        '/a/fake/download/directory', '53.0a1', 1, 'multi', 'arm'
    ) == {
        'apk': {
            'url': 'https://ftp.mozilla.org/pub/mobile/nightly/latest-mozilla-central-android-api-15/fennec-53.0a1.multi.android-arm.apk',
            'download_location': '/a/fake/download/directory/fennec-53.0a1.multi.android-arm.apk',
        },
        'checksums': {
            'url': 'https://ftp.mozilla.org/pub/mobile/nightly/latest-mozilla-central-android-api-15/fennec-53.0a1.multi.android-arm.checksums',
            'download_location': '/a/fake/download/directory/fennec-53.0a1.multi.android-arm.checksums',
        },
    }


def test_craft_apk_and_checksums_file_names():
    assert _craft_apk_and_checksums_file_names('50.0b8', 'multi', 'arm') == {
        'apk': 'fennec-50.0b8.multi.android-arm.apk',
        'checksums': 'fennec-50.0b8.multi.android-arm.checksums',
    }
    assert _craft_apk_and_checksums_file_names('51.0a2', 'en-US', 'x86') == {
        'apk': 'fennec-51.0a2.en-US.android-i386.apk',
        'checksums': 'fennec-51.0a2.en-US.android-i386.checksums',
    }


def test_get_architecture_in_file_name():
    assert _get_architecture_in_file_name('arm') == 'arm'
    assert _get_architecture_in_file_name('x86') == 'i386'


@pytest.mark.parametrize('checksum_file,raises', ((
    os.path.join(DATA_DIR, 'checksums.old'), False,
), (
    os.path.join(DATA_DIR, 'checksums.tc'), False,
), (
    os.path.join(DATA_DIR, 'checksums.broken'), True,
)))
def test_check_apk_against_checksum_file(checksum_file, raises):
    try:
        # check_apk nukes the checksum file, so make a copy first
        temp_dir = mkdtemp()
        temp_checksum_file = os.path.join(temp_dir, os.path.basename(checksum_file))
        shutil.copyfile(checksum_file, temp_checksum_file)

        # paths in checksum are relatives, so make a copy of the blob as well
        temp_apk_file = os.path.join(temp_dir, os.path.basename(CHECKSUM_APK))
        shutil.copyfile(CHECKSUM_APK, temp_apk_file)
        with mock.patch.object(shutil, 'rmtree'):
            if raises:
                with pytest.raises(CheckSumMismatch):
                    check_apk_against_checksum_file(temp_apk_file, temp_checksum_file)
            else:
                check_apk_against_checksum_file(temp_apk_file, temp_checksum_file)
    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.parametrize('checksum_file', (
    os.path.join(DATA_DIR, 'checksums.old'),
    os.path.join(DATA_DIR, 'checksums.tc'),
    os.path.join(DATA_DIR, 'SHA512SUMS'),
))
def test_fetch_checksum_from_file(checksum_file):
    assert _fetch_checksum_from_file(checksum_file, CHECKSUM_APK) == \
        'd5ee2608eb21d827deef87732dc4796c7209098b8db39f95c3fac87c0dc7b186f2b097f0a52e856e6ac504ff3039a3e23936615be55a172665cdd0250f3a4379'


@pytest.mark.parametrize('checksum_file, apk_file, expected', (
    (
        '/a/fake/download/directory/target.checksums',
        '/a/fake/download/directory/target.apk',
        'target.apk'
    ),
    (
        '/a/fake/download/directory/fennec-50.0b8.multi.android-arm.checksums',
        '/a/fake/download/directory/fennec-50.0b8.multi.android-arm.apk',
        'fennec-50.0b8.multi.android-arm.apk'
    ),
    (
        '/a/fake/download/directory/target.checksums',
        '/a/fake/download/directory/a-subdir/target.apk',
        'a-subdir/target.apk'
    ),
))
def test_take_out_common_path(checksum_file, apk_file, expected):
    assert _take_out_common_path(checksum_file, apk_file) == expected
