import logging

import unittest
from unittest.mock import MagicMock

from pushapkworker.script import craft_push_config, craft_logging_config


class ScriptTest(unittest.TestCase):
    def test_craft_push_config(self):
        context = MagicMock()
        context.config = {
            'google_play_service_account': 'a@service-account.org',
            'google_play_certificate': '/path/to/certificate.p12',
            'google_play_package_name': 'org.mozilla.random_firefox'
        }
        context.task = {
            'payload': {
                'google_play_track': 'alpha'
            }
        }
        apks = {
            'x86': '/path/to/x86.apk',
            'arm_v15': '/path/to/arm_v15.apk',
        }

        self.assertEqual(craft_push_config(context, apks), {
            'service_account': 'a@service-account.org',
            'credentials': '/path/to/certificate.p12',
            'track': 'alpha',
            'package_name': 'org.mozilla.random_firefox',
            'apk_x86': '/path/to/x86.apk',
            'apk_arm_v15': '/path/to/arm_v15.apk',
        })

    def test_craft_logging_config(self):
        context = MagicMock()
        context.config = {'verbose': True}

        self.assertEqual(craft_logging_config(context), {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'level': logging.DEBUG
        })

        context.config = {'verbose': False}
        self.assertEqual(craft_logging_config(context), {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'level': logging.INFO
        })
