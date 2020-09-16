import json
import pytest
from zipfile import ZipFile

import addonscript.xpi as xpi


@pytest.fixture(scope="function")
def fake_xpi():
    path = "fake_target.langpack.xpi"
    with ZipFile(path, "r") as langpack_xpi:
        manifest = langpack_xpi.getinfo("manifest.json")
        with langpack_xpi.open(manifest) as f:
            contents = f.read().decode("utf-8")
            return json.loads(contents)


@pytest.fixture(scope="function")
def fake_build_xpi():
    path = "fake_target.langpack.xpi"
    manifest_payload = {
        'applications': {
            'gecko': {
                'id': 'langpack-en-US@firefox.mozilla.org',
                'strict_max_version': '81.*',
                'strict_min_version': '81.0'
            }
        },
        'description': 'Language pack for Firefox for en-US',
        'langpack_id': 'en-US',
        'languages': {
            'en-US': {
                'version': '20200910193722'
            }
        },
        'manifest_version': 2,
        'name': 'English (US) Language Pack',
        'version': '81.0buildid20200910180444'
    }

    # TODO: drop this into a json file, zip it and change to `xpi`


@pytest.mark.parametrize(
    "version,expected_version",
    (
        ("81.0buildid20200914232702", "81.0"),
        ("81.0", "81.0"),
        ("81.0buildid", "81.0"),
        ("81.0buildid202009142", "81.0"),
        ("81.0a1buildid202009142", "81.0"),
        ("81.0b1buildid202009142", "81.0"),
    ),
)
def test_get_stripped_version(version, expected_version):
    assert xpi.get_stripped_version(version) == expected_version


def test_get_langpack_info(fake_xpi):
    path = "fake_target.langpack.xpi"
    langpack = xpi.get_langpack_info(path)
    assert langpack["locale"] == fake_xpi["langpack_id"]
    assert langpack["version"] == fake_xpi["version"]
    assert langpack["id"] == fake_xpi["applications"]["gecko"]["id"]
