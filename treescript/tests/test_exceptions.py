import pytest
from scriptworker_client.exceptions import TaskError, TaskVerificationError

import treescript.exceptions as exceptions


@pytest.mark.parametrize(
    "exc,from_", ((exceptions.TaskVerificationError, TaskVerificationError), (exceptions.FailedSubprocess, TaskError), (exceptions.TreeScriptError, TaskError))
)
def test_exception(exc, from_):
    a = exc("x")
    assert isinstance(a, from_)
