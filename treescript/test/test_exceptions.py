import pytest

from scriptworker.exceptions import ScriptWorkerTaskException
from treescript.exceptions import (
    TaskVerificationError,
    FailedSubprocess
)


@pytest.mark.parametrize('exc', (TaskVerificationError, FailedSubprocess))
def test_exception(exc):
    a = exc('x')
    assert isinstance(a, ScriptWorkerTaskException)
