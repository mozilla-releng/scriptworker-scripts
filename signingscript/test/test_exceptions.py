import pytest

from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.exceptions import (
    TaskVerificationError,
    SigningServerError,
    FailedSubprocess
)


@pytest.mark.parametrize('exc', (TaskVerificationError, SigningServerError, FailedSubprocess))
def test_exception(exc):
    a = exc('x')
    assert isinstance(a, ScriptWorkerTaskException)
