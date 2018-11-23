import logging
import subprocess

from pushapkscript.exceptions import SignatureError
from pushapkscript.task import extract_android_product_from_scopes

log = logging.getLogger(__name__)


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


def _check_certificate_via_return_code(return_code, command_output, binary_path, apk_path, certificate_alias, keystore_path):
    if return_code != 0:
        log.critical(command_output)
        raise SignatureError(
            '{} doesn\'t verify APK "{}". It compared certificate against "{}", located in keystore "{}".\
            Maybe you\'re now allowed to push such APKs on this instance?'
            .format(binary_path, apk_path, certificate_alias, keystore_path)
        )

    log.info('The signature of "{}" comes from the correct alias "{}"'.format(apk_path, certificate_alias))


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
