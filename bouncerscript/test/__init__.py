import aiohttp
import asyncio
import pytest

from scriptworker.context import Context
from bouncerscript.utils import load_json
from scriptworker.test import event_loop


assert event_loop  # silence flake8


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


async def return_true_async(context, product):
    return True


def get_fake_valid_config(jobtype):
    return load_json(path="bouncerscript/test/fake_{}_config.json".format(jobtype))


def get_fake_valid_task(jobtype):
    return load_json(path="bouncerscript/test/test_work_dir/task_{}.json".format(jobtype))


@pytest.yield_fixture(scope='function')
def submission_context():
    context = Context()
    context.task = get_fake_valid_task("submission")
    context.config = get_fake_valid_config("submission")

    yield context


@pytest.yield_fixture(scope='function')
def aliases_context():
    context = Context()
    context.task = get_fake_valid_task("aliases")
    context.config = get_fake_valid_config("aliases")

    yield context


@pytest.fixture(scope='function')
def fake_ClientError_throwing_session(event_loop):
    @asyncio.coroutine
    def _fake_request(method, url, *args, **kwargs):
        raise aiohttp.ClientError

    session = aiohttp.ClientSession()
    session._request = _fake_request
    return session


@pytest.fixture(scope='function')
def fake_TimeoutError_throwing_session(event_loop):
    @asyncio.coroutine
    def _fake_request(method, url, *args, **kwargs):
        raise aiohttp.ServerTimeoutError

    session = aiohttp.ClientSession()
    session._request = _fake_request
    return session
