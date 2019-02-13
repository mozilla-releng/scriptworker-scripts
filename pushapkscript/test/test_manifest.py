import os
import pytest

from zipfile import ZipFile

from pushapkscript import manifest
from pushapkscript.exceptions import SignatureError


@pytest.mark.parametrize('does_apk_have_expected_digest, raises', (
    (True, False),
    (False, True),
))
def test_verify(monkeypatch, does_apk_have_expected_digest, raises):
    monkeypatch.setattr(manifest, '_does_apk_have_expected_digest', lambda _, __: does_apk_have_expected_digest)
    product_config = {
        'digest_algorithm': 'SHA-1'
    }

    if raises:
        with pytest.raises(SignatureError):
            manifest.verify(product_config, '/some/apk_path')
    else:
        manifest.verify(product_config, '/some/apk_path')


@pytest.mark.parametrize('manifest_data, digest, expected', ((
    '',
    'SHA1',
    False,
), (
    """Manifest-Version: 1.0
Built-By: Generated-by-Autograph
Created-By: go.mozilla.org/autograph

Name: AndroidManifest.xml
SHA-256-Digest: some-base64-sha256
SHA1-Digest: some-base64-sha1

Name: application.ini
SHA-256-Digest: another-base64-sha256
SHA1-Digest: another-base64-sha1
""",
    'SHA1',
    True,
), (
    """Manifest-Version: 1.0
Built-By: Generated-by-Autograph
Created-By: go.mozilla.org/autograph

Name: AndroidManifest.xml
SHA-256-Digest: some-base64-sha256
SHA1-Digest: some-base64-sha1

Name: application.ini
SHA-256-Digest: another-base64-sha256
SHA1-Digest: another-base64-sha1
""",
    'SHA-256',
    True,
), (
    """Manifest-Version: 1.0
Built-By: Generated-by-Autograph
Created-By: go.mozilla.org/autograph

Name: AndroidManifest.xml
SHA-256-Digest: some-base64-sha256

Name: application.ini
SHA-256-Digest: another-base64-sha256
""",
    'SHA1',
    False,
), (
    """Manifest-Version: 1.0
Built-By: Generated-by-Autograph
Created-By: go.mozilla.org/autograph

Name: AndroidManifest.xml
SHA1-Digest: some-base64-sha1

Name: application.ini
SHA1-Digest: another-base64-sha1
""",
    'SHA-256',
    False,
)))
def test_does_apk_have_expected_digest(tmpdir, manifest_data, digest, expected):
    apk_path = os.path.join(tmpdir, 'app.apk')
    with ZipFile(apk_path, mode='w') as zip:
        zip.writestr('META-INF/MANIFEST.MF', manifest_data)

    assert manifest._does_apk_have_expected_digest(apk_path, digest) == expected


@pytest.mark.parametrize('lines, expected', ((
    [],
    {},
), (
    [
        'Manifest-Version: 1.0\n',
        'Built-By: Generated-by-Autograph\n',
        'Created-By: go.mozilla.org/autograph\n',
        '\n',
    ],
    {},
), (
    [
        'Manifest-Version: 1.0\n',
        'Built-By: Generated-by-Autograph\n',
        'Created-By: go.mozilla.org/autograph\n',
        '\n',
        'Name: AndroidManifest.xml\n',
        'SHA1-Digest: some-base64-hash\n',
        '\n',
        'Name: application.ini\n',
        'SHA1-Digest: another-base64-hash\n',
        '\n',
    ],
    {
        'AndroidManifest.xml': {'SHA1-Digest': 'some-base64-hash'},
        'application.ini': {'SHA1-Digest': 'another-base64-hash'},
    },
), (
    [
        'Manifest-Version: 1.0\n',
        'Built-By: Generated-by-Autograph\n',
        'Created-By: go.mozilla.org/autograph\n',
        '\n',
        'Name: AndroidManifest.xml\n',
        'SHA-256-Digest: some-base64-sha256\n',
        'SHA1-Digest: some-base64-sha1\n',
        '\n',
        'Name: application.ini\n',
        'SHA-256-Digest: another-base64-sha256\n',
        'SHA1-Digest: another-base64-sha1\n',
        '\n',
    ],
    {
        'AndroidManifest.xml': {
            'SHA-256-Digest': 'some-base64-sha256',
            'SHA1-Digest': 'some-base64-sha1',
        },
        'application.ini': {
            'SHA-256-Digest': 'another-base64-sha256',
            'SHA1-Digest': 'another-base64-sha1',
        },
    },
), (
    [
        'Manifest-Version: 1.0\n',
        'Built-By: Generated-by-Autograph\n',
        'Created-By: go.mozilla.org/autograph\n',
        'Name: AndroidManifest.xml\n',
        'SHA1-Digest: some-base64-hash\n',
        'Name: application.ini\n',
        'SHA1-Digest: another-base64-hash\n',
    ],
    {
        'AndroidManifest.xml': {'SHA1-Digest': 'some-base64-hash'},
        'application.ini': {'SHA1-Digest': 'another-base64-hash'},
    },
), (
    [
        'Manifest-Version: 1.0\n',
        'Built-By: Generated-by-Autograph\n',
        'Created-By: go.mozilla.org/autograph\n',
        '\n',
        'Name: AndroidManifest.xml\n',
        'SHA1-Digest: some-base64-hash\n',
        '\n',
        'Name: some/super-duper/real/looooooooooooooooooooooooooooooooooooooooo\n',
        ' ng-file-name.png\n',
        'SHA1-Digest: another-base64-hash\n',
    ],
    {
        'AndroidManifest.xml': {'SHA1-Digest': 'some-base64-hash'},
        'some/super-duper/real/looooooooooooooooooooooooooooooooooooooooong-file-name.png': {
            'SHA1-Digest': 'another-base64-hash',
        },
    },
), (
    [
        'Manifest-Version: 1.0\n',
        'Created-By: 1.6.0_41 (Sun Microsystems Inc.)\n',
        '\n',
        'Name: application.ini\n',
        'SHA1-Digest: another-base64-hash\n',
        '\n',
        'Name: AndroidManifest.xml\n',
        'SHA1-Digest: some-base64-hash\n',
    ],
    {
        'AndroidManifest.xml': {'SHA1-Digest': 'some-base64-hash'},
        'application.ini': {'SHA1-Digest': 'another-base64-hash'},
    },
)))
def test_parse_manifest_lines(lines, expected):
    assert manifest._parse_manifest_lines(lines) == expected


@pytest.mark.parametrize('digest, manifest_data, expected', ((
    'SHA1',
    {},
    False
), (
    'SHA1',
    {
        'AndroidManifest.xml': {'SHA1-Digest': 'some-base64-hash'},
        'application.ini': {'SHA1-Digest': 'some-base64-hash'},
    },
    True
), (
    'SHA-256',
    {
        'AndroidManifest.xml': {'SHA-256-Digest': 'some-base64-hash'},
        'application.ini': {'SHA-256-Digest': 'some-base64-hash'},
    },
    True
), (
    'SHA1',
    {
        'AndroidManifest.xml': {
            'SHA1-Digest': 'some-base64-hash',
            'SHA-256-Digest': 'some-base64-hash',
        },
        'application.ini': {
            'SHA1-Digest': 'some-base64-hash',
            'SHA-256-Digest': 'some-base64-hash',
        },
    },
    True
), (
    'SHA-256',
    {
        'AndroidManifest.xml': {
            'SHA1-Digest': 'some-base64-hash',
            'SHA-256-Digest': 'some-base64-hash',
        },
        'application.ini': {
            'SHA1-Digest': 'some-base64-hash',
            'SHA-256-Digest': 'some-base64-hash',
        },
    },
    True
), (
    'SHA1',
    {
        'AndroidManifest.xml': {'SHA-256-Digest': 'some-base64-hash'},
        'application.ini': {'SHA-256-Digest': 'some-base64-hash'},
    },
    False,
), (
    'SHA1',
    # One file doesn't have SHA1
    {
        'AndroidManifest.xml': {
            'SHA1-Digest': 'some-base64-hash',
            'SHA-256-Digest': 'some-base64-hash',
        },
        'application.ini': {'SHA-256-Digest': 'some-base64-hash'},
    },
    False
)))
def test_is_digest_present(digest, manifest_data, expected):
    assert manifest._is_digest_present(digest, manifest_data) == expected
