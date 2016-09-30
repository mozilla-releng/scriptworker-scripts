import unittest
from unittest.mock import MagicMock, patch

import subprocess

from pushapkworker.jarsigner import JarSigner
from pushapkworker.exceptions import SignatureError


class JarSignerTest(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.context.config = {
            'jarsigner_binary': '/path/to/jarsigner',
            'jarsigner_key_store': '/path/to/keystore',
            'jarsigner_certificate_aliases': {
                'aurora': 'aurora_alias',
                'beta': 'beta_alias',
                'release': 'release_alias',
            }
        }
        self.jar_signer = JarSigner(self.context)

    def test_allows_binary_to_be_set(self):
        binary_path = '/path/to/jarsigner'
        self.context.config['jarsigner_binary'] = binary_path
        jar_signer = JarSigner(self.context)
        self.assertEqual(jar_signer.binary_path, binary_path)

    def test_verify_should_call_executable_with_right_arguments(self):
        for channel, alias in self.context.config['jarsigner_certificate_aliases'].items():
            with patch('subprocess.run') as run:
                run.return_value = MagicMock()
                run.return_value.returncode = 0
                self.jar_signer.verify('/path/to/apk', channel)

                run.assert_called_with([
                    '/path/to/jarsigner', '-verify', '-strict', '-keystore', '/path/to/keystore', '/path/to/apk', alias
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_verify_should_call_executable_with_defaults_arguments(self):
        minimal_context = MagicMock()
        minimal_context.config = {
            'jarsigner_key_store': '/path/to/keystore',
        }

        jar_signer = JarSigner(minimal_context)

        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            jar_signer.verify('/path/to/apk', channel='aurora')

            run.assert_called_with([
                'jarsigner', '-verify', '-strict', '-keystore', '/path/to/keystore', '/path/to/apk', 'nightly'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_raises_error_when_return_code_is_not_0(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 1

            with self.assertRaises(SignatureError):
                self.jar_signer.verify('/path/to/apk', channel='aurora')
