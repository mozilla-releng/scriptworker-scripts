import logging
import re
import subprocess

from pushapkscript.exceptions import SignatureError

log = logging.getLogger(__name__)

DIGEST_ALGORITHM_REGEX = re.compile(r'\s*Digest algorithm: (\S+)$', re.MULTILINE)


def verify(context, apk_path, channel):
    binary_path, keystore_path, certificate_aliases = _pluck_configuration(context)
    certificate_alias = certificate_aliases[channel]

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
    _check_digest_algorithm(command_output, apk_path)


def _check_certificate_via_return_code(return_code, command_output, binary_path, apk_path, certificate_alias, keystore_path):
    if return_code != 0:
        log.critical(command_output)
        raise SignatureError(
            '{} doesn\'t verify APK "{}". It compared certificate against "{}", located in keystore "{}"'
            .format(binary_path, apk_path, certificate_alias, keystore_path)
        )

    log.info('The signature of "{}" comes from the correct alias "{}"'.format(apk_path, certificate_alias))


def _check_digest_algorithm(command_output, apk_path):
    # This prevents https://bugzilla.mozilla.org/show_bug.cgi?id=1332916
    match_result = DIGEST_ALGORITHM_REGEX.search(command_output)
    if match_result is None:
        log.critical(command_output)
        raise SignatureError('Could not find what digest algorithm was used to sign this APK')

    digest_algorithm = match_result.group(1)
    if digest_algorithm != 'SHA1':
        log.critical(command_output)
        raise SignatureError(
            'Wrong digest algorithm: SHA1 digest is expected, but "{}" was found'.format(digest_algorithm)
        )

    log.info('The signature of "{}" contains the correct digest algorithm'.format(apk_path))


def _pluck_configuration(context):
    keystore_path = context.config['jarsigner_key_store']
    # Uses jarsigner in PATH if config doesn't provide it
    binary_path = context.config.get('jarsigner_binary', 'jarsigner')
    certificate_aliases = context.config.get('jarsigner_certificate_aliases', {
        'aurora': 'nightly',
        'beta': 'nightly',
        'release': 'release'
    })

    return binary_path, keystore_path, certificate_aliases
