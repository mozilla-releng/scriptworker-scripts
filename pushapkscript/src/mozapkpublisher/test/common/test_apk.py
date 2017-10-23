import os
import pytest

from shutil import rmtree
from tempfile import mkdtemp, NamedTemporaryFile
from zipfile import ZipFile

from mozapkpublisher.common import apk
from mozapkpublisher.common.apk import check_if_apk_is_multilocale, _get_unique_locales, check_if_apk_has_claimed_architecture, \
    get_apk_architecture, _extract_architecture_from_paths
from mozapkpublisher.common.exceptions import NoLocaleFound, NotMultiLocaleApk, BadApk


MANIFEST_PARTIAL_CONTENT = '''
content extensions toolkit/content/extensions/
locale alerts en-US en-US/locale/en-US/alerts/
locale autoconfig en-US en-US/locale/en-US/autoconfig/
locale pluginproblem en-US en-US/locale/en-US/pluginproblem/
locale branding an an/locale/branding/
locale branding as as/locale/branding/
locale branding bn-IN bn-IN/locale/branding/
locale branding en-GB en-GB/locale/branding/
locale browser en-GB en-GB/locale/en-GB/browser/
override chrome://global/locale/about.dtd chrome://browser/locale/overrides/about.dtd
'''


def _create_apk_with_locale_content(temp_dir, manifest_content):
    with NamedTemporaryFile('w') as manifest:
        manifest.write(manifest_content)
        manifest.seek(0)

        omni_ja_path = os.path.join(temp_dir, 'omni.ja')
        with ZipFile(omni_ja_path, 'w') as omni_ja:
            omni_ja.write(manifest.name, 'chrome/chrome.manifest')

    apk_path = os.path.join(temp_dir, 'fennec.apk')
    with ZipFile(apk_path, 'w') as apk:
        apk.write(omni_ja_path, 'assets/omni.ja')

    return apk_path


def _create_apk_with_architecture_content(temp_dir, architecture=None):
    random_file_in_lib = os.path.join(temp_dir, 'libmozglue.so')
    with open(random_file_in_lib, 'w'):
        pass

    apk_path = os.path.join(temp_dir, 'fennec-{}.apk'.format(architecture))
    with ZipFile(apk_path, 'w') as apk:
        if architecture is not None:
            apk.write(random_file_in_lib, 'lib/{}/libmozglue.so'.format(architecture))

    return apk_path


def test_check_if_apk_is_multilocale():
    temp_dir = mkdtemp()
    check_if_apk_is_multilocale(_create_apk_with_locale_content(temp_dir, MANIFEST_PARTIAL_CONTENT))

    with pytest.raises(NoLocaleFound):
        check_if_apk_is_multilocale(_create_apk_with_locale_content(temp_dir, 'non-locale stuff'))

    with pytest.raises(NotMultiLocaleApk):
        check_if_apk_is_multilocale(_create_apk_with_locale_content(temp_dir, '''
locale alerts en-US en-US/locale/en-US/alerts/
locale autoconfig en-US en-US/locale/en-US/autoconfig/
'''))

    rmtree(temp_dir)


def test_get_unique_locales():
    manifest_raw_lines = MANIFEST_PARTIAL_CONTENT.split('\n')
    manifest_raw_lines = [line.encode() for line in manifest_raw_lines]
    assert sorted(_get_unique_locales(manifest_raw_lines)) == ['an', 'as', 'bn-IN', 'en-GB', 'en-US']


def test_check_if_apk_has_claimed_architecture(monkeypatch):
    monkeypatch.setattr(apk, 'get_apk_architecture', lambda _: 'x86')

    check_if_apk_has_claimed_architecture('some.apk', 'x86')

    with pytest.raises(BadApk):
        check_if_apk_has_claimed_architecture('some.apk', 'armv7_v15')

    with pytest.raises(BadApk):
        monkeypatch.setattr(apk, 'get_apk_architecture', lambda _: 'unsupported-arch')
        check_if_apk_has_claimed_architecture('some.apk', 'x86')


def test_get_apk_architecture():
    temp_dir = mkdtemp()

    assert get_apk_architecture(_create_apk_with_architecture_content(temp_dir, 'x86')) == 'x86'
    assert get_apk_architecture(_create_apk_with_architecture_content(temp_dir, 'armeabi-v7a')) == 'armeabi-v7a'

    with pytest.raises(BadApk):
        get_apk_architecture(_create_apk_with_architecture_content(temp_dir, architecture=None))

    rmtree(temp_dir)


def test_extract_architecture_from_paths():
    assert _extract_architecture_from_paths(
        '/path/to/apk', ['lib/armeabi-v7a/libmozglue.so', 'lib/armeabi-v7a/libplugin-container.so']
    ) == 'armeabi-v7a'
    assert _extract_architecture_from_paths(
        '/path/to/apk', ['lib/x86/libmozglue.so', 'lib/x86/libplugin-container.so']
    ) == 'x86'

    with pytest.raises(BadApk):
        _extract_architecture_from_paths('/path/to/apk', ['lib/'])

    with pytest.raises(BadApk):
        _extract_architecture_from_paths('/path/to/apk', ['lib/armeabi-v7a/libmozglue.so', 'lib/x86/libmozglue.so'])
