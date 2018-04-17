import pytest

from scriptworker.exceptions import TaskVerificationError
from unittest.mock import MagicMock

from pushsnapscript.task import pluck_channel, is_allowed_to_push_to_snap_store


@pytest.mark.parametrize('raises, scopes, expected', (
    (False, ['project:releng:snapcraft:firefox:candidate'], 'candidate'),
    (False, ['project:releng:snapcraft:firefox:beta'], 'beta'),
    (False, ['project:releng:snapcraft:firefox:esr'], 'esr'),
    (False, ['project:releng:snapcraft:firefox:mock'], 'mock'),
    (False, ['project:releng:snapcraft:firefox:beta', 'some:other:scope'], 'beta'),

    (True, ['project:releng:snapcraft:firefox:beta', 'project:releng:snapcraft:firefox:beta'], None),
    (True, ['project:releng:snapcraft:firefox:beta', 'project:releng:snapcraft:firefox:candidate'], None),
    (True, ['project:releng:snapcraft:firefox:edge'], None),
    (True, ['project:releng:snapcraft:firefox:stable'], None),
))
def test_pluck_channel(raises, scopes, expected):
    task = {'scopes': scopes}
    if raises:
        with pytest.raises(TaskVerificationError):
            pluck_channel(task)
    else:
        assert pluck_channel(task) == expected


@pytest.mark.parametrize('channel, expected', (
    ('beta', True),
    ('candidate', True),
    ('esr', True),

    ('mock', False),
))
def test_is_allowed_to_push_to_snap_store(channel, expected):
    assert is_allowed_to_push_to_snap_store(channel=channel) == expected

    context = MagicMock()
    context.task = {'scopes': ['project:releng:snapcraft:firefox:{}'.format(channel)]}
    assert is_allowed_to_push_to_snap_store(context=context) == expected
