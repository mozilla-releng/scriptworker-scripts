import pytest

from scriptworker import artifacts
from scriptworker.exceptions import TaskVerificationError

from pushsnapscript.artifacts import get_snap_file_path


@pytest.mark.parametrize('raises, returned, expected', (
    (False, ({'taskId': ['/path/to/file.snap']}, {}), '/path/to/file.snap'),
    (False, ({'taskId': ['/path/to/file.snap', '/some/other/file.txt']}, {}), '/path/to/file.snap'),
    (False, ({'taskId': ['/path/to/file.snap'], 'otherTaskId': '/some/other/file.txt'}, {}), '/path/to/file.snap'),

    (True, ({}, {'taskId': ['/path/to/file.snap']}), None),
    (True, ({'taskId': ['/some/other/file.txt']}, {}), None),
    (True, ({'taskId': ['/path/to/file.snap'], 'otherTaskId': ['/some/other/file.snap']}, {}), None),
))
def test_get_snap_file_path(monkeypatch, raises, returned, expected):
    context = None

    monkeypatch.setattr(artifacts, 'get_upstream_artifacts_full_paths_per_task_id', lambda _: returned)
    if raises:
        with pytest.raises(TaskVerificationError):
            get_snap_file_path(context)
    else:
        assert get_snap_file_path(context) == expected
