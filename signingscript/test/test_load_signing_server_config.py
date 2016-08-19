import os
from scriptworker.context import Context
from signingscript.utils import load_signing_server_config


def test_load_signing_server_config():
    context = Context()
    context.config = {
        'signing_server_config': os.path.join(os.path.dirname(__file__),
                                              "example_server_config.json")
    }
    cfg = load_signing_server_config(context)
    assert cfg["dep"][0].server == "server1:9000"
    assert cfg["dep"][1].user == "user2"
    assert cfg["notdep"][0].password == "pass1"
    assert cfg["notdep"][1].formats == ["f2", "f3"]
