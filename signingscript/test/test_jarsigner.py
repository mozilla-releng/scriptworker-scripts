import unittest
from unittest.mock import MagicMock, patch

import subprocess

from signingscript.jarsigner import JarSigner
from signingscript.exceptions import SignatureError


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class JarSignerTest(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock()
        self.context.config = {
            'jarsigner_key_store': '/path/to/keystore',
            'jarsigner_certificate_alias': 'certificate_alias'
        }
        self.jar_signer = JarSigner(self.context)

    def test_default_binary_relies_on_path(self):
        self.assertEqual(self.jar_signer.binary_path, 'jarsigner')

    def test_allows_binary_to_be_set(self):
        binary_path = '/path/to/jarsigner'
        self.context.config['jarsigner_binary'] = binary_path
        jar_signer = JarSigner(self.context)
        self.assertEqual(jar_signer.binary_path, binary_path)

    def test_verify_should_call_executable_with_right_arguments(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 0
            self.jar_signer.verify('/path/to/apk')

            run.assert_called_with([
                'jarsigner', '-verify', '-strict', '-keystore', '/path/to/keystore', '/path/to/apk', 'certificate_alias'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def test_raises_error_when_return_code_is_not_0(self):
        with patch('subprocess.run') as run:
            run.return_value = MagicMock()
            run.return_value.returncode = 1

            with self.assertRaises(SignatureError):
                self.jar_signer.verify('/path/to/apk')
