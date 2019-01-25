import pytest
import os
import re
import shutil
import tempfile

from distutils.util import strtobool

from mozapkpublisher.get_apk import GetAPK


@pytest.mark.asyncio
@pytest.mark.skipif(strtobool(os.environ.get('SKIP_NETWORK_TESTS', 'true')), reason='Tests requiring network are skipped')
@pytest.mark.parametrize('version, build, arch, apks_file_regexes', (
    # Re-enable latest_nightly once bug 1346752 is fixed
    # ({'latest_nightly': True, 'arch': 'x86'}, (r'fennec-\d{2}\.0a1\.multi\.android-i386\.apk',)),

    # Pre-Fennec 53.0b1
    ('52.0', '2', 'arm', (r'fennec-52\.0\.multi\.android-arm\.apk',)),
    ('53.0b1', '3', 'arm', (r'fennec-53\.0b1\.multi\.android-arm\.apk',)),
))
async def test_download_files(version, build, arch, apks_file_regexes):
    temp_dir = tempfile.mkdtemp()
    await GetAPK(version, None, build, arch, 'multi', temp_dir).run()
    files_in_temp_dir = [
        name for name in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, name))
    ]
    assert len(files_in_temp_dir) == len(apks_file_regexes)

    for regex in apks_file_regexes:
        assert any(re.match(regex, file_name) for file_name in files_in_temp_dir)

    shutil.rmtree(temp_dir)
