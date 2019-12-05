import io
import logging
import re

from zipfile import ZipFile
from pushapkscript.exceptions import SignatureError


log = logging.getLogger(__name__)

_NAME_MARKER = 'Name: '
_DIGEST_MARKER_PATTERN = re.compile(r'\S+-Digest: ')


def verify(product_config, apk_path):
    # This prevents https://bugzilla.mozilla.org/show_bug.cgi?id=1332916
    expected_digest_algorithm = product_config['digest_algorithm']
    if not _does_apk_have_expected_digest(apk_path, expected_digest_algorithm):
        raise SignatureError(
            'Wrong digest algorithm: "{}" digest is expected, but it was not found'.format(expected_digest_algorithm)
        )

    log.info('The signature of "{}" contains the correct digest algorithm ({})'.format(
        apk_path, expected_digest_algorithm
    ))


def _does_apk_have_expected_digest(apk_path, expected_digest):
    with ZipFile(apk_path) as zip:
        with zip.open('META-INF/MANIFEST.MF') as f:
            # readline doesn't return a py3 str
            manifest_lines = [line for line in io.TextIOWrapper(f, 'utf-8')]

    manifest = _parse_manifest_lines(manifest_lines)
    return _is_digest_present(expected_digest, manifest)


def _parse_manifest_lines(manifest_lines):
    manifest = {}
    current_file = None
    for line in manifest_lines:
        line = line.rstrip('\n')     # remove trailing EOL
        # XXX Headers at the top aren't parsed
        if line.startswith(_NAME_MARKER):
            current_file = line[len(_NAME_MARKER):]
        elif current_file:
            if line.startswith(' '):
                current_file = current_file + line.lstrip()
            elif _DIGEST_MARKER_PATTERN.match(line):
                digest, hash = line.split(': ')
                manifest.setdefault(current_file, {})[digest] = hash

    return manifest


def _is_digest_present(expected_digest, parsed_manifest):
    if not parsed_manifest:
        return False

    expected_digest = '{}-Digest'.format(expected_digest)
    return all(expected_digest in entry for entry in parsed_manifest.values())
