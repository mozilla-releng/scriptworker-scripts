import os
import pytest

from distutils.util import strtobool


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def skip_when_no_network(function):
    return pytest.mark.skipif(
        strtobool(os.environ.get('SKIP_NETWORK_TESTS', 'true')),
        reason='Tests requiring network are skipped'
    )(function)
