import pytest
from scriptworker import artifacts
from scriptworker.exceptions import TaskVerificationError

from pushmsixscript.artifacts import get_msix_file_path


@pytest.mark.parametrize(
    "raises, returned, expected",
    (
        (False, ({"taskId": ["/path/to/file.store.msix"]}, {}), "/path/to/file.store.msix"),
        (False, ({"taskId": ["/path/to/file.store.msix", "/some/other/file.txt"]}, {}), "/path/to/file.store.msix"),
        (False, ({"taskId": ["/path/to/file.store.msix"], "otherTaskId": "/some/other/file.txt"}, {}), "/path/to/file.store.msix"),
        (True, ({}, {"taskId": ["/path/to/file.store.msix"]}), None),
        (True, ({"taskId": ["/some/other/file.txt"]}, {}), None),
        (True, ({"taskId": ["/path/to/file.store.msix"], "otherTaskId": ["/some/other/file.store.msix"]}, {}), None),
    ),
)
def test_get_msix_file_path(monkeypatch, raises, returned, expected):
    context = None

    monkeypatch.setattr(artifacts, "get_upstream_artifacts_full_paths_per_task_id", lambda _: returned)
    if raises:
        with pytest.raises(TaskVerificationError):
            get_msix_file_path(context)
    else:
        assert get_msix_file_path(context) == expected
