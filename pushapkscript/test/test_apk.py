import os
import pytest

from tempfile import TemporaryDirectory
from zipfile import ZipFile

from pushapkscript.exceptions import TaskVerificationError
from pushapkscript.apk import sort_and_check_apks_per_architectures, _convert_architecture_to_mozapkpublisher, \
    _extract_architecture_from_paths, _get_apk_architecture, _check_architectures_are_valid


def _create_apk(temp_dir, architecture=None):
    random_file_in_lib = os.path.join(temp_dir, 'libmozglue.so')
    with open(random_file_in_lib, 'w'):
        pass

    apk_path = os.path.join(temp_dir, 'fennec-{}.apk'.format(architecture))
    with ZipFile(apk_path, 'w') as apk:
        if architecture is not None:
            apk.write(random_file_in_lib, 'lib/{}/libmozglue.so'.format(architecture))

    return apk_path


def test_sort_and_check_apks_per_architectures():
    with TemporaryDirectory() as temp_dir:
        x86_apk_path = _create_apk(temp_dir, 'x86')
        arm_apk_path = _create_apk(temp_dir, 'armeabi-v7a')

        assert sort_and_check_apks_per_architectures([x86_apk_path, arm_apk_path], 'release') == {
            'x86': x86_apk_path,
            'armv7_v15': arm_apk_path,
        }


def test_convert_architecture_to_mozapkpublisher():
    assert _convert_architecture_to_mozapkpublisher('x86') == 'x86'
    assert _convert_architecture_to_mozapkpublisher('armeabi-v7a') == 'armv7_v15'


def test_get_apk_architecture():
    with TemporaryDirectory() as temp_dir:
        assert _get_apk_architecture(_create_apk(temp_dir, 'x86')) == 'x86'
        assert _get_apk_architecture(_create_apk(temp_dir, 'armeabi-v7a')) == 'armeabi-v7a'

        with pytest.raises(TaskVerificationError):
            _get_apk_architecture(_create_apk(temp_dir, architecture=None))


def test_extract_architecture_from_paths():
    assert _extract_architecture_from_paths(
        '/path/to/apk', ['lib/armeabi-v7a/libmozglue.so', 'lib/armeabi-v7a/libplugin-container.so']
    ) == 'armeabi-v7a'
    assert _extract_architecture_from_paths(
        '/path/to/apk', ['lib/x86/libmozglue.so', 'lib/x86/libplugin-container.so']
    ) == 'x86'

    with pytest.raises(TaskVerificationError):
        _extract_architecture_from_paths('/path/to/apk', ['lib/'])

    with pytest.raises(TaskVerificationError):
        _extract_architecture_from_paths('/path/to/apk', ['lib/armeabi-v7a/libmozglue.so', 'lib/x86/libmozglue.so'])


def test_check_architectures_are_valid():
    _check_architectures_are_valid(['x86', 'armv7_v15'], 'aurora')  # No failure expected
    _check_architectures_are_valid(['x86', 'armv7_v15'], 'beta')
    _check_architectures_are_valid(['x86', 'armv7_v15'], 'release')

    with pytest.raises(TaskVerificationError):
        _check_architectures_are_valid(['x86'], 'non-existing-channel')

    with pytest.raises(TaskVerificationError):
        _check_architectures_are_valid(['x86'], 'release')

    with pytest.raises(TaskVerificationError):
        _check_architectures_are_valid(['x86', 'armv7_v11'], 'release')

    with pytest.raises(TaskVerificationError):
        _check_architectures_are_valid(['x86', 'armv7_v11', 'armv7_v15'], 'release')
