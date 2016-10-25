import unittest
from unittest.mock import MagicMock, patch

import subprocess

from pushapkscript import jarsigner
from pushapkscript.exceptions import SignatureError


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

        self.minimal_context = MagicMock()
        self.minimal_context.config = {
            'jarsigner_key_store': '/path/to/keystore',
        }

    def test_verify_should_call_executable_with_right_arguments(self):
        for channel, alias in self.context.config['jarsigner_certificate_aliases'].items():
            with patch('subprocess.run') as run:
                run.return_value = MagicMock()
                run.return_value.returncode = 0
                jarsigner.verify(self.context, '/path/to/apk', channel)

                run.assert_called_with([
                    '/path/to/jarsigner', '-verify', '-strict', '-keystore', '/path/to/keystore', '/path/to/apk', alias
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_verify_should_call_executable_with_defaults_arguments(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            jarsigner.verify(self.minimal_context, '/path/to/apk', channel='aurora')

            run.assert_called_with([
                'jarsigner', '-verify', '-strict', '-keystore', '/path/to/keystore', '/path/to/apk', 'nightly'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_raises_error_when_return_code_is_not_0(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 1

            with self.assertRaises(SignatureError):
                jarsigner.verify(self.context, '/path/to/apk', channel='aurora')

    def test_pluck_configuration_sets_every_argument(self):
        self.assertEqual(
            jarsigner._pluck_configuration(self.context),
            (
                '/path/to/jarsigner',
                '/path/to/keystore',
                {
                    'aurora': 'aurora_alias',
                    'beta': 'beta_alias',
                    'release': 'release_alias',
                }
            )
        )

    def test_pluck_configuration_uses_defaults(self):
        self.assertEqual(
            jarsigner._pluck_configuration(self.minimal_context),
            (
                'jarsigner',
                '/path/to/keystore',
                {
                    'aurora': 'nightly',
                    'beta': 'nightly',
                    'release': 'release',
                }
            )
        )
