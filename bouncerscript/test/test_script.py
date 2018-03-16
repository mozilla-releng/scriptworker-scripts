import logging
import mock
import pytest
import sys

from unittest.mock import MagicMock
import bouncerscript.script as bscript
from bouncerscript.script import (
    craft_logging_config, main, bouncer_submission, bouncer_aliases, async_main
)
from bouncerscript.test import (
    submission_context, noop_async, aliases_context, return_true_async
)
from scriptworker.test import (
    event_loop, fake_session,
)
from scriptworker.exceptions import (
    ScriptWorkerTaskException,
)


assert event_loop, fake_session  # silence flake8
assert submission_context  # silence flake8
assert aliases_context  # silence flake8


# craft_logging_config {{{1
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


def test_invalid_args():
    args = ['only-one-arg']
    with mock.patch.object(sys, 'argv', args):
        with pytest.raises(SystemExit):
            main(name='__main__')

    args = ['only-one-arg', 'bouncerscript/test/fake_submission_config.json']
    with mock.patch.object(sys, 'argv', args):
        with mock.patch('bouncerscript.script.async_main', new=noop_async):
            main(name='__main__')


# main {{{1
def test_main(submission_context, event_loop, fake_session):
    async def fake_async_main_with_exception(context):
        raise ScriptWorkerTaskException("This is wrong, the answer is 42")

    with mock.patch('bouncerscript.script.async_main', new=noop_async):
        main(name='__main__', config_path='bouncerscript/test/fake_submission_config.json')

    with mock.patch('bouncerscript.script.async_main', new=fake_async_main_with_exception):
        try:
            main(name='__main__', config_path='bouncerscript/test/fake_submission_config.json')
        except SystemExit as exc:
            assert exc.code == 1


# bouncer_submission {{{1
@pytest.mark.asyncio
async def test_bouncer_submission(submission_context, mocker):
    mocker.patch.object(bscript, 'does_product_exists', new=noop_async)
    mocker.patch.object(bscript, 'api_add_product', new=noop_async)
    mocker.patch.object(bscript, 'api_add_location', new=noop_async)
    await bouncer_submission(submission_context)

    mocker.patch.object(bscript, 'does_product_exists', new=return_true_async)
    await bouncer_submission(submission_context)


# bouncer_aliases {{{1
@pytest.mark.asyncio
async def test_bouncer_aliases(aliases_context, mocker):
    mocker.patch.object(bscript, 'api_update_alias', new=noop_async)
    await bouncer_aliases(aliases_context)


# async_main {{{1
@pytest.mark.asyncio
async def test_async_main(submission_context, mocker):
    mocker.patch.object(bscript, 'bouncer_submission', new=noop_async)
    mocker.patch.object(bscript, 'does_product_exists', new=noop_async)
    mocker.patch.object(bscript, 'api_add_product', new=noop_async)
    mocker.patch.object(bscript, 'api_add_location', new=noop_async)

    await async_main(submission_context)
