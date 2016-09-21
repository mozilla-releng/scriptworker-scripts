import logging
import subprocess

from signingscript.exceptions import SignatureError

log = logging.getLogger(__name__)


class JarSigner(object):
    def __init__(self, context):
        self.keystore_path = context.config['jarsigner_key_store']
        self.certificate_alias = context.config['jarsigner_certificate_alias']
        # Uses jarsigner in PATH if config doesn't provide it
        try:
            self.binary_path = context.config['jarsigner_binary']
        except KeyError:
            self.binary_path = 'jarsigner'

    def verify(self, apk_path):
        completed_process = subprocess.run([
            self.binary_path, '-verify', '-strict', '-keystore', self.keystore_path, apk_path, self.certificate_alias
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        if completed_process.returncode != 0:
            log.critical(completed_process.stdout)
            raise SignatureError(
                '{} doesn\'t verify apk "{}". It compared certificate against "{}", located in keystore "{}"'
                .format(self.binary_path, apk_path, self.certificate_alias, self.keystore_path)
            )
