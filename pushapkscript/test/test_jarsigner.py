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
                'dep': 'dep_alias',
            },
            'taskcluster_scope_prefixes': ['project:releng:googleplay:'],
        }
        self.context.task = {
            'scopes': ['project:releng:googleplay:aurora'],
            'payload': {},
        }

        self.minimal_context = MagicMock()
        self.minimal_context.config = {
            'jarsigner_key_store': '/path/to/keystore',
            'taskcluster_scope_prefixes': ['project:releng:googleplay:'],
        }
        self.minimal_context.task = {
            'scopes': ['project:releng:googleplay:aurora'],
            'payload': {},
        }

    def test_verify_should_call_executable_with_right_arguments(self):
        for android_product, alias in self.context.config['jarsigner_certificate_aliases'].items():
            self.context.task['scopes'] = ['project:releng:googleplay:{}'.format(android_product)]
            with patch('subprocess.run') as run:
                run.return_value = MagicMock()
                run.return_value.returncode = 0
                run.return_value.stdout = '''
                    smk      632 Mon Feb 01 12:54:21 CET 2016 application.ini
                        Digest algorithm: SHA1
                '''
                jarsigner.verify(self.context, '/path/to/apk')

                run.assert_called_with([
                    '/path/to/jarsigner', '-verify', '-strict', '-verbose', '-keystore', '/path/to/keystore', '/path/to/apk', alias
                ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_verify_should_call_executable_with_defaults_arguments(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            run.return_value.stdout = 'Digest algorithm: SHA1'
            jarsigner.verify(self.minimal_context, '/path/to/apk')

            run.assert_called_with([
                'jarsigner', '-verify', '-strict', '-verbose', '-keystore', '/path/to/keystore', '/path/to/apk', 'nightly'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_raises_error_when_return_code_is_not_0(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 1

            with self.assertRaises(SignatureError):
                jarsigner.verify(self.context, '/path/to/apk')

    def test_pluck_configuration_sets_every_argument(self):
        self.assertEqual(
            jarsigner._pluck_configuration(self.context),
            (
                '/path/to/jarsigner',
                '/path/to/keystore',
                'aurora_alias',
            )
        )

    def test_pluck_configuration_uses_defaults(self):
        self.assertEqual(
            jarsigner._pluck_configuration(self.minimal_context),
            (
                'jarsigner',
                '/path/to/keystore',
                'nightly',
            )
        )

    def test_pluck_configuration_accepts_certificate_alias(self):
        context = MagicMock()
        context.config = {
            'jarsigner_key_store': '/path/to/keystore',
            'taskcluster_scope_prefixes': ['project:releng:googleplay:'],
            'jarsigner_certificate_aliases': {},
        }
        context.task = {
            'scopes': ['project:releng:googleplay:fenix'],
            'payload': {
                'certificate_alias': 'fenix-beta'
            },
        }
        self.assertEqual(
            jarsigner._pluck_configuration(context),
            (
                'jarsigner',
                '/path/to/keystore',
                'fenix-beta'
            )
        )

    def test_pluck_configuration_raise_multiple_alias_source(self):
        context = MagicMock()
        context.config = {
            'jarsigner_key_store': '/path/to/keystore',
            'taskcluster_scope_prefixes': ['project:releng:googleplay:'],
            'jarsigner_certificate_aliases': {
                'aurora': 'aurora_alias',
            },
        }
        context.task = {
            'scopes': ['project:releng:googleplay:aurora'],
            'payload': {
                'certificate_alias': 'firefox-aurora'
            },
        }

        with self.assertRaises(ValueError):
            jarsigner._pluck_configuration(context)

    def test_pluck_configuration_raise_no_alias_source(self):
        context = MagicMock()
        context.config = {
            'jarsigner_key_store': '/path/to/keystore',
            'taskcluster_scope_prefixes': ['project:releng:googleplay:'],
            'jarsigner_certificate_aliases': {},
        }
        context.task = {
            'scopes': ['project:releng:googleplay:aurora'],
            'payload': {},
        }
        with self.assertRaises(ValueError):
            jarsigner._pluck_configuration(context)
