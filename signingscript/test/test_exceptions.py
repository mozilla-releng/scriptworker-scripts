import pytest

from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.exceptions import (
    SigningServerError,
    FailedSubprocess
)


@pytest.mark.parametrize('exc', (SigningServerError, FailedSubprocess))
def test_exception(exc):
    a = exc('x')
    assert isinstance(a, ScriptWorkerTaskException)
