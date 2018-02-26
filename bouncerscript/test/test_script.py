import logging
import mock

from unittest.mock import MagicMock
from bouncerscript.script import (
    craft_logging_config, main
)
from bouncerscript.test import (
    submission_context,
)
from scriptworker.test import (
    event_loop, fake_session,
)
from scriptworker.exceptions import (
    ScriptWorkerTaskException,
)


assert event_loop, fake_session  # silence flake8
assert submission_context  # silence flake8


def test_craft_logging_config():
    context = MagicMock()
    context.config = {'verbose': True}

    assert craft_logging_config(context) == {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.DEBUG
    }

    context.config = {'verbose': False}
    assert craft_logging_config(context) == {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.INFO
    }


# main {{{1
def test_main(submission_context, event_loop, fake_session):
    async def fake_async_main(context):
        pass

    async def fake_async_main_with_exception(context):
        raise ScriptWorkerTaskException("This is wrong, the answer is 42")

    with mock.patch('bouncerscript.script.async_main', new=fake_async_main):
        main(name='__main__', config_path='bouncerscript/test/fake_submission_config.json')

    with mock.patch('bouncerscript.script.async_main', new=fake_async_main_with_exception):
        try:
            main(name='__main__', config_path='bouncerscript/test/fake_submission_config.json')
        except SystemExit as exc:
            assert exc.code == 1
