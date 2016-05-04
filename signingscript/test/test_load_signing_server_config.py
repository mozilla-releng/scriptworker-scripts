from unittest import TestCase
import os
from signingworker.utils import load_signing_server_config


class TestLoadSigningServerConfig(TestCase):
    def test_load_signing_server_config(self):
        cfg_file = os.path.join(os.path.dirname(__file__),
                                "example_server_config.json")
        cfg = load_signing_server_config(cfg_file)
        self.assertEqual(cfg["dep"][0].server, "server1:9000")
        self.assertEqual(cfg["dep"][1].user, "user2")
        self.assertEqual(cfg["notdep"][0].password, "pass1")
        self.assertEqual(cfg["notdep"][1].formats, ["f2", "f3"])
