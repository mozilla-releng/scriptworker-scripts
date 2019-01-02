import aiohttp
import asyncio
import bouncerscript
import json
import os
import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


async def return_empty_list_async(*args, **kwargs):
    return []


async def return_true_async(*args):
    return True


async def return_false_async(*args):
    return False


def raise_sync(*args, **kwargs):
    raise ScriptWorkerTaskException()


def counted(f):
    def wrapped(*args, **kwargs):
        wrapped.calls += 1
        return f(*args, **kwargs)
    wrapped.calls = 0
    return wrapped


@counted
async def toggled_boolean_async(*args, **kwargs):
    if toggled_boolean_async.calls & 1:
        return False
    else:
        return True


def return_true_sync(*args):
    return True


def return_false_sync(*args):
    return False


def get_fake_valid_config():
    data_dir = os.path.join(os.path.dirname(bouncerscript.__file__), 'data')
    config = {
        'schema_files': {
            'submission': os.path.join(data_dir, 'bouncer_submission_task_schema.json'),
            'aliases': os.path.join(data_dir, 'bouncer_aliases_task_schema.json'),
            'locations': os.path.join(data_dir, 'bouncer_locations_task_schema.json'),
        }
    }
    config.update(load_json(path="bouncerscript/test/fake_config.json"))
    return config


def get_fake_valid_task(jobtype):
    return load_json(path="bouncerscript/test/test_work_dir/task_{}.json".format(jobtype))


@pytest.yield_fixture(scope='function')
def submission_context():
    context = Context()
    context.task = get_fake_valid_task("submission")
    context.config = get_fake_valid_config()

    yield context


@pytest.yield_fixture(scope='function')
def aliases_context():
    context = Context()
    context.task = get_fake_valid_task("aliases")
    context.config = get_fake_valid_config()

    yield context


@pytest.yield_fixture(scope='function')
def locations_context():
    context = Context()
    context.task = get_fake_valid_task("locations")
    context.config = get_fake_valid_config()

    yield context


@pytest.fixture(scope='function')
def fake_ClientError_throwing_session():
    @asyncio.coroutine
    def _fake_request(method, url, *args, **kwargs):
        raise aiohttp.ClientError

    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    session._request = _fake_request
    return session


@pytest.fixture(scope='function')
def fake_TimeoutError_throwing_session():
    @asyncio.coroutine
    def _fake_request(method, url, *args, **kwargs):
        raise aiohttp.ServerTimeoutError

    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    session._request = _fake_request
    return session


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)
