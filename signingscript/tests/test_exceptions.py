import pytest
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.exceptions import FailedSubprocess, SigningServerError


@pytest.mark.parametrize("exc", (SigningServerError, FailedSubprocess))
def test_exception(exc):
    a = exc("x")
    assert isinstance(a, ScriptWorkerTaskException)
