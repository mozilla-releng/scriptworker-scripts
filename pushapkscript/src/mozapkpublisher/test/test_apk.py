import os
import pytest

from shutil import rmtree
from tempfile import mkdtemp, NamedTemporaryFile
from zipfile import ZipFile

from mozapkpublisher.apk import check_if_apk_is_multilocale, _get_unique_locales
from mozapkpublisher.exceptions import NoLocaleFound, NotMultiLocaleApk


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


def _create_apk(temp_dir, manifest_content):
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


def test_check_if_apk_is_multilocale():
    temp_dir = mkdtemp()
    check_if_apk_is_multilocale(_create_apk(temp_dir, MANIFEST_PARTIAL_CONTENT))

    with pytest.raises(NoLocaleFound):
        check_if_apk_is_multilocale(_create_apk(temp_dir, 'non-locale stuff'))

    with pytest.raises(NotMultiLocaleApk):
        check_if_apk_is_multilocale(_create_apk(temp_dir, '''
locale alerts en-US en-US/locale/en-US/alerts/
locale autoconfig en-US en-US/locale/en-US/autoconfig/
'''))

    rmtree(temp_dir)


def test_get_unique_locales():
    manifest_raw_lines = MANIFEST_PARTIAL_CONTENT.split('\n')
    manifest_raw_lines = [line.encode() for line in manifest_raw_lines]
    assert sorted(_get_unique_locales(manifest_raw_lines)) == ['an', 'as', 'bn-IN', 'en-GB', 'en-US']
