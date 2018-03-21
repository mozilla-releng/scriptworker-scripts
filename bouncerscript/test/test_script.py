import mock
import pytest

import bouncerscript.script as bscript
from bouncerscript.script import (
    main, bouncer_submission, bouncer_aliases, async_main
)
from bouncerscript.test import (
    submission_context, noop_async, aliases_context, return_true
)
from scriptworker.test import (
    event_loop, fake_session,
)
from scriptworker.exceptions import (
    ScriptWorkerTaskException, TaskVerificationError
)


assert event_loop, fake_session  # silence flake8
assert submission_context  # silence flake8
assert aliases_context  # silence flake8


# main {{{1
def test_main(submission_context, event_loop, fake_session):
    async def fake_async_main_with_exception(context):
        raise ScriptWorkerTaskException("This is wrong, the answer is 42")

    with mock.patch('bouncerscript.script.async_main', new=noop_async):
        main(config_path='bouncerscript/test/fake_config.json')

    with mock.patch('bouncerscript.script.async_main', new=fake_async_main_with_exception):
        try:
            main(config_path='bouncerscript/test/fake_config.json')
        except SystemExit as exc:
            assert exc.code == 1


# bouncer_submission {{{1
@pytest.mark.asyncio
async def test_bouncer_submission(submission_context, mocker):
    mocker.patch.object(bscript, 'does_product_exists', new=noop_async)
    mocker.patch.object(bscript, 'api_add_product', new=noop_async)
    mocker.patch.object(bscript, 'api_add_location', new=noop_async)
    await bouncer_submission(submission_context)

    mocker.patch.object(bscript, 'does_product_exists', new=return_true)
    await bouncer_submission(submission_context)


# bouncer_aliases {{{1
@pytest.mark.asyncio
async def test_bouncer_aliases(aliases_context, mocker):
    mocker.patch.object(bscript, 'api_update_alias', new=noop_async)
    await bouncer_aliases(aliases_context)


# async_main {{{1
@pytest.mark.asyncio
async def test_async_main(submission_context, mocker, event_loop):
    mocker.patch.object(bscript, 'bouncer_submission', new=noop_async)
    mocker.patch.object(bscript, 'does_product_exists', new=noop_async)
    mocker.patch.object(bscript, 'api_add_product', new=noop_async)
    mocker.patch.object(bscript, 'api_add_location', new=noop_async)

    await async_main(submission_context)

    mocker.patch.object(bscript, 'action_map', new={})
    with pytest.raises(TaskVerificationError):
        await async_main(submission_context)
