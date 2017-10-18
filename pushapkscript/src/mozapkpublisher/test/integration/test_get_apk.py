import pytest
import os
import re
import shutil
import tempfile

from distutils.util import strtobool

from mozapkpublisher.get_apk import GetAPK


@pytest.mark.skipif(strtobool(os.environ.get('SKIP_NETWORK_TESTS', 'true')), reason='Tests requiring network are skipped')
@pytest.mark.parametrize('get_apk_args, apks_file_regexes', (
    # Re-enable latest_nightly once bug 1346752 is fixed
    # ({'latest_nightly': True, 'arch': 'x86'}, (r'fennec-\d{2}\.0a1\.multi\.android-i386\.apk',)),

    # Pre-Fennec 53.0b1
    ({'version': '52.0', 'build': '2', 'arch': 'arm'}, (r'fennec-52\.0\.multi\.android-arm\.apk',)),
    ({'version': '53.0b1', 'build': '3', 'arch': 'arm'}, (r'fennec-53\.0b1\.multi\.android-arm\.apk',)),
))
def test_download_files(get_apk_args, apks_file_regexes):
    temp_dir = tempfile.mkdtemp()
    get_apk_args['output-directory'] = temp_dir
    GetAPK(get_apk_args).run()
    files_in_temp_dir = [
        name for name in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, name))
    ]
    assert len(files_in_temp_dir) == len(apks_file_regexes)

    for regex in apks_file_regexes:
        assert any(re.match(regex, file_name) for file_name in files_in_temp_dir)

    shutil.rmtree(temp_dir)
