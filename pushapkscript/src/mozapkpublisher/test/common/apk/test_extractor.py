import os
import pytest

from androguard.core.bytecodes import apk as androguard
from configparser import ConfigParser
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import MagicMock
from zipfile import ZipFile

from mozapkpublisher.common.apk.extractor import extract_metadata, _extract_architecture, _extract_architecture_from_paths, \
    _extract_firefox_version, _extract_firefox_build_id, _extract_value_from_application_ini, _extract_locales, \
    _get_unique_locales
from mozapkpublisher.common.exceptions import NoLocaleFound, BadApk


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
    with ZipFile(apk_path, 'a') as apk_zip:
        apk_zip.write(omni_ja_path, 'assets/omni.ja')

    return apk_path


def _create_apk_with_architecture_content(temp_dir, architecture=None):
    random_file_in_lib = os.path.join(temp_dir, 'libmozglue.so')
    with open(random_file_in_lib, 'w'):
        pass

    apk_path = os.path.join(temp_dir, 'fennec.apk')
    with ZipFile(apk_path, 'a') as apk_zip:
        if architecture is not None:
            apk_zip.write(random_file_in_lib, 'lib/{}/libmozglue.so'.format(architecture))

    return apk_path


def _create_apk_with_application_ini(temp_dir, config_data=None):
    config = ConfigParser()
    config.read_dict(config_data)
    application_ini_path = os.path.join(temp_dir, 'application.ini')
    with open(application_ini_path, 'w') as application_ini_file:
        config.write(application_ini_file)

    apk_path = os.path.join(temp_dir, 'fennec.apk')
    with ZipFile(apk_path, 'a') as apk_zip:
        apk_zip.write(application_ini_path, 'application.ini')

    return apk_path


def _create_apk_with_all_metadata(temp_dir):
    _create_apk_with_locale_content(temp_dir, manifest_content=MANIFEST_PARTIAL_CONTENT)
    _create_apk_with_architecture_content(temp_dir, architecture='x86')
    return _create_apk_with_application_ini(temp_dir, config_data={
        'App': {
            'BuildID': '20171112125738',
            'Version': '57.0',
        },
    })


def test_extract_metadata(monkeypatch):
    androguard_mock = MagicMock()
    androguard_mock.get_package = lambda: 'org.mozilla.firefox'
    androguard_mock.get_min_sdk_version = lambda: 16
    androguard_mock.get_androidversion_code = lambda: '2015523300'
    monkeypatch.setattr(androguard, 'APK', lambda _: androguard_mock)

    with TemporaryDirectory() as temp_dir:
        apk_file = _create_apk_with_all_metadata(temp_dir)
        assert extract_metadata(apk_file) == {
            'api_level': 16,
            'architecture': 'x86',
            'firefox_build_id': '20171112125738',
            'firefox_version': '57.0',
            'locales': ('an', 'as', 'bn-IN', 'en-GB', 'en-US'),
            'package_name': 'org.mozilla.firefox',
            'version_code': '2015523300',
        }


@pytest.mark.parametrize('architecture', (('x86', 'armeabi-v7a')))
def test_get_apk_architecture(architecture):
    with TemporaryDirectory() as temp_dir:
        apk_file = _create_apk_with_architecture_content(temp_dir, architecture)
        with ZipFile(apk_file) as apk_zip:
            assert _extract_architecture(apk_zip, '/original/path.apk') == architecture


def test_bad_get_apk_architecture():
    with TemporaryDirectory() as temp_dir:
        apk_file_without_arch = _create_apk_with_architecture_content(temp_dir, architecture=None)
        with ZipFile(apk_file_without_arch) as apk_zip_without_arch:
            with pytest.raises(BadApk):
                _extract_architecture(apk_zip_without_arch, '/original/path.apk')


@pytest.mark.parametrize('paths, expected', ((
    ['lib/armeabi-v7a/libmozglue.so', 'lib/armeabi-v7a/libplugin-container.so'], 'armeabi-v7a',
), (
    ['lib/x86/libmozglue.so', 'lib/x86/libplugin-container.so'], 'x86',
)))
def test_extract_architecture_from_paths(paths, expected):
    assert _extract_architecture_from_paths('/path/to/apk', paths) == expected


@pytest.mark.parametrize('paths', (
    ['lib/'],
    ['lib/armeabi-v7a/libmozglue.so', 'lib/x86/libplugin-container.so'],
))
def test_bad_extract_architecture_from_paths(paths):
    with pytest.raises(BadApk):
        _extract_architecture_from_paths('/path/to/apk', paths)


def test_extract_firefox_version():
    with TemporaryDirectory() as temp_dir:
        apk_path = _create_apk_with_application_ini(temp_dir, config_data={
            'App': {
                'Version': '57.0',
            },
        })
        with ZipFile(apk_path) as apk_zip:
            assert _extract_firefox_version(apk_zip) == '57.0'


def test_extract_firefox_build_id():
    with TemporaryDirectory() as temp_dir:
        apk_path = _create_apk_with_application_ini(temp_dir, config_data={
            'App': {
                'BuildID': '20171112125738',
            },
        })
        with ZipFile(apk_path) as apk_zip:
            assert _extract_firefox_build_id(apk_zip) == '20171112125738'


def test_extract_value_from_application_ini():
    with TemporaryDirectory() as temp_dir:
        apk_path = _create_apk_with_application_ini(temp_dir, config_data={
            'SomeSection': {
                'somekey': 'some value',
                'someotherkey': 'some other value',
            },
            'SomeOtherSection': {
                'someotherkeyinothersection': 'some other value in other section'
            },
        })
        with ZipFile(apk_path) as apk_zip:
            assert _extract_value_from_application_ini(apk_zip, 'SomeSection.somekey') == 'some value'


@pytest.mark.parametrize('manifest_content, expected_locales', ((
    MANIFEST_PARTIAL_CONTENT, ('an', 'as', 'bn-IN', 'en-GB', 'en-US'),
), (
    '''locale alerts en-US en-US/locale/en-US/alerts/
    locale autoconfig en-US en-US/locale/en-US/autoconfig/
    ''', ('en-US',)
)))
def test_extract_locales(manifest_content, expected_locales):
    with TemporaryDirectory() as temp_dir:
        apk_file = _create_apk_with_locale_content(temp_dir, manifest_content)
        with ZipFile(apk_file) as apk_zip:
            assert _extract_locales(apk_zip) == expected_locales


def test_bad_extract_locales():
    with TemporaryDirectory() as temp_dir:
        apk_file = _create_apk_with_locale_content(temp_dir, 'non-locale stuff')
        with ZipFile(apk_file) as apk_zip:
            with pytest.raises(NoLocaleFound):
                _extract_locales(apk_zip)


def test_get_unique_locales():
    manifest_raw_lines = MANIFEST_PARTIAL_CONTENT.split('\n')
    manifest_raw_lines = [line.encode() for line in manifest_raw_lines]
    assert _get_unique_locales(manifest_raw_lines) == ('an', 'as', 'bn-IN', 'en-GB', 'en-US')
