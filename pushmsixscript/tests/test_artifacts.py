import pytest
from scriptworker_client import artifacts
from scriptworker_client.exceptions import TaskVerificationError

from pushmsixscript.artifacts import get_msix_file_paths


@pytest.mark.parametrize(
    "raises, returned, expected",
    (
        (False, ({"taskId": ["/path/to/file.store.msix"]}, {}), ["/path/to/file.store.msix"]),
        (False, ({"taskId": ["/path/to/file.store.msix", "/some/other/file.txt"]}, {}), ["/path/to/file.store.msix"]),
        (False, ({"taskId": ["/path/to/file.store.msix"], "otherTaskId": "/some/other/file.txt"}, {}), ["/path/to/file.store.msix"]),
        (True, ({}, {"taskId": ["/path/to/file.store.msix"]}), None),
        (True, ({"taskId": ["/some/other/file.txt"]}, {}), None),
        (
            False,
            ({"taskId": ["/path/to/file.store.msix"], "otherTaskId": ["/some/other/file.store.msix"]}, {}),
            ["/path/to/file.store.msix", "/some/other/file.store.msix"],
        ),
    ),
)
def test_get_msix_file_paths(monkeypatch, raises, returned, expected):
    monkeypatch.setattr(artifacts, "get_upstream_artifacts_full_paths_per_task_id", lambda c, t: returned)
    if raises:
        with pytest.raises(TaskVerificationError):
            get_msix_file_paths({}, {})
    else:
        assert get_msix_file_paths({}, {}) == expected
