import mock
import os
import pytest
import shutil
from tempfile import mkdtemp

from mozapkpublisher.exceptions import CheckSumMismatch, WrongArgumentGiven
from mozapkpublisher.get_apk import GetAPK, _craft_apk_and_checksums_file_names, _get_architecture_in_file_name, check_apk_against_checksum_file

VALID_CONFIG = {'version': '50.0b8'}
CHECKSUM_APK = os.path.join(os.path.dirname(__file__), 'data', 'blob')
get_apk = GetAPK(VALID_CONFIG)


def test_mutually_exclusive_group():
    with pytest.raises(WrongArgumentGiven):
        GetAPK({'clean': True, 'version': True})

    with pytest.raises(WrongArgumentGiven):
        GetAPK({'clean': True, 'latest_nightly': True})

    with pytest.raises(WrongArgumentGiven):
        GetAPK({'version': True, 'latest_nightly': True})

    with pytest.raises(WrongArgumentGiven):
        GetAPK({'latest_nightly': True, 'latest_aurora': True})


def test_generate_apk_base_url():
    assert GetAPK({'latest_nightly': True}).generate_apk_base_url('52.0a1', None, 'multi', 'x86') == \
        'https://ftp.mozilla.org/pub/mobile/nightly/latest-mozilla-central-android-x86'

    assert GetAPK({'latest_aurora': True}).generate_apk_base_url('51.0a2', None, 'en-US', 'api-15') == \
        'https://ftp.mozilla.org/pub/mobile/nightly/latest-mozilla-aurora-android-api-15'

    assert GetAPK({'version': '50.0b8'}).generate_apk_base_url('50.0b8', 1, 'multi', 'api-15') == \
        'https://ftp.mozilla.org/pub/mobile/candidates/50.0b8-candidates/build1/android-api-15/multi'


def test_get_api_suffix():
    assert get_apk.get_api_suffix('arm') == ['api-15']
    assert get_apk.get_api_suffix('x86') == ['x86']


def test_craft_apk_and_checksums_file_names():
    assert _craft_apk_and_checksums_file_names('50.0b8', 'multi', 'arm') == \
        ['fennec-50.0b8.multi.android-arm.apk', 'fennec-50.0b8.multi.android-arm.checksums']
    assert _craft_apk_and_checksums_file_names('51.0a2', 'en-US', 'x86') == \
        ['fennec-51.0a2.en-US.android-i386.apk', 'fennec-51.0a2.en-US.android-i386.checksums']


def test_get_architecture_in_file_name():
    assert _get_architecture_in_file_name('arm') == 'arm'
    assert _get_architecture_in_file_name('x86') == 'i386'


@pytest.mark.parametrize('checksum_file,raises', ((
    os.path.join(os.path.dirname(__file__), 'data', 'checksums.old'), False,
), (
    os.path.join(os.path.dirname(__file__), 'data', 'checksums.tc'), False,
), (
    os.path.join(os.path.dirname(__file__), 'data', 'checksums.broken'), True,
)))
def test_check_apk_against_checksum_file(checksum_file, raises):
    try:
        # check_apk nukes the checksum file, so make a copy first
        temp_dir = mkdtemp()
        cfile = os.path.join(temp_dir, os.path.basename(checksum_file))
        shutil.copyfile(checksum_file, cfile)
        with mock.patch.object(shutil, 'rmtree'):
            if raises:
                with pytest.raises(CheckSumMismatch):
                    check_apk_against_checksum_file(CHECKSUM_APK, cfile)
            else:
                assert check_apk_against_checksum_file(CHECKSUM_APK, cfile) is None
    finally:
        shutil.rmtree(temp_dir)
