import os
import pytest

from distutils.util import strtobool


def skip_when_no_autograph_server(function):
    return pytest.mark.skipif(
        not strtobool(os.environ.get('AUTOGRAPH_INTEGRATION', 'false')),
        reason='Tests requiring an Autograph server are skipped'
    )(function)
