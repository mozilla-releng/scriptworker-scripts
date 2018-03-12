import pytest

from scriptworker.exceptions import TaskVerificationError

from pushsnapscript.task import pluck_channel


@pytest.mark.parametrize('raises, scopes, expected', (
    (False, ['project:releng:snapcraft:firefox:candidate'], 'candidate'),
    (False, ['project:releng:snapcraft:firefox:edge'], 'edge'),
    (False, ['project:releng:snapcraft:firefox:edge', 'some:other:scope'], 'edge'),

    (True, ['project:releng:snapcraft:firefox:edge', 'project:releng:snapcraft:firefox:edge'], None),
    (True, ['project:releng:snapcraft:firefox:edge', 'project:releng:snapcraft:firefox:candidate'], None),
    (True, ['project:releng:snapcraft:firefox:stable'], None),
    (True, ['project:releng:snapcraft:firefox:beta'], None),
))
def test_pluck_channel(raises, scopes, expected):
    task = {'scopes': scopes}
    if raises:
        with pytest.raises(TaskVerificationError):
            pluck_channel(task)
    else:
        assert pluck_channel(task) == expected
