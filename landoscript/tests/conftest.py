import pytest


@pytest.fixture(scope="function")
def config():
    config = {
        "lando_api": "https://lando.fake",
    }
    return config
