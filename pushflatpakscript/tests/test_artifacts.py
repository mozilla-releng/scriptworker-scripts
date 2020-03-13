import pytest
from scriptworker import artifacts
from scriptworker.exceptions import TaskVerificationError

from pushflatpakscript.artifacts import get_flatpak_file_path


@pytest.mark.parametrize(
    "raises, returned, expected",
    (
        (False, ({"taskId": ["/path/to/file.flatpak.tar.xz"]}, {}), "/path/to/file.flatpak.tar.xz"),
        (False, ({"taskId": ["/path/to/file.flatpak.tar.xz", "/some/other/file.txt"]}, {}), "/path/to/file.flatpak.tar.xz"),
        (False, ({"taskId": ["/path/to/file.flatpak.tar.xz"], "otherTaskId": "/some/other/file.txt"}, {}), "/path/to/file.flatpak.tar.xz"),
        (True, ({}, {"taskId": ["/path/to/file.flatpak.tar.xz"]}), None),
        (True, ({"taskId": ["/some/other/file.txt"]}, {}), None),
        (True, ({"taskId": ["/path/to/file.flatpak.tar.xz"], "otherTaskId": ["/some/other/file.flatpak.tar.xz"]}, {}), None),
    ),
)
def test_get_flatpak_file_path(monkeypatch, raises, returned, expected):
    context = None

    monkeypatch.setattr(artifacts, "get_upstream_artifacts_full_paths_per_task_id", lambda _: returned)
    if raises:
        with pytest.raises(TaskVerificationError):
            get_flatpak_file_path(context)
    else:
        assert get_flatpak_file_path(context) == expected
