import logging
import re
import subprocess

from pushapkscript.exceptions import SignatureError
from pushapkscript.task import extract_android_product_from_scopes

log = logging.getLogger(__name__)

DIGEST_ALGORITHM_REGEX = re.compile(r'\s*Digest algorithm: (\S+)$', re.MULTILINE)

_DIGEST_ALGORITHM_PER_ANDROID_PRODUCT = {
    'aurora': 'SHA1',
    'beta': 'SHA1',
    'release': 'SHA1',
    'dep': 'SHA1',

    'focus': 'SHA-256',
}


def verify(context, apk_path):
    binary_path, keystore_path, certificate_aliases, android_product = _pluck_configuration(context)
    certificate_alias = certificate_aliases[android_product]

    completed_process = subprocess.run([
        binary_path, '-verify', '-strict',
        '-verbose',     # Needed to check the digest algorithm
        '-keystore', keystore_path,
        apk_path,
        certificate_alias
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    command_output = completed_process.stdout
    _check_certificate_via_return_code(
        completed_process.returncode, command_output, binary_path, apk_path, certificate_alias, keystore_path
    )
    _check_digest_algorithm(command_output, apk_path, android_product)


def _check_certificate_via_return_code(return_code, command_output, binary_path, apk_path, certificate_alias, keystore_path):
    if return_code != 0:
        log.critical(command_output)
        raise SignatureError(
            '{} doesn\'t verify APK "{}". It compared certificate against "{}", located in keystore "{}".\
            Maybe you\'re now allowed to push such APKs on this instance?'
            .format(binary_path, apk_path, certificate_alias, keystore_path)
        )

    log.info('The signature of "{}" comes from the correct alias "{}"'.format(apk_path, certificate_alias))


def _check_digest_algorithm(command_output, apk_path, android_product):
    # This prevents https://bugzilla.mozilla.org/show_bug.cgi?id=1332916
    match_result = DIGEST_ALGORITHM_REGEX.search(command_output)
    if match_result is None:
        log.critical(command_output)
        raise SignatureError('Could not find what digest algorithm was used to sign this APK')

    digest_algorithm = match_result.group(1)
    expected_digest_algorithm = _DIGEST_ALGORITHM_PER_ANDROID_PRODUCT[android_product]
    if digest_algorithm != expected_digest_algorithm:
        log.critical(command_output)
        raise SignatureError(
            'Wrong digest algorithm: "{}" digest is expected, but "{}" was found'.format(expected_digest_algorithm, digest_algorithm)
        )

    log.info('The signature of "{}" contains the correct digest algorithm'.format(apk_path))


def _pluck_configuration(context):
    keystore_path = context.config['jarsigner_key_store']
    # Uses jarsigner in PATH if config doesn't provide it
    binary_path = context.config.get('jarsigner_binary', 'jarsigner')
    certificate_aliases = context.config.get('jarsigner_certificate_aliases', {
        'aurora': 'nightly',
        'beta': 'nightly',
        'release': 'release',
        'dep': 'dep',
    })
    android_product = extract_android_product_from_scopes(context)
    return binary_path, keystore_path, certificate_aliases, android_product
