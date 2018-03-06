from beetmoverscript.utils import load_json
import pytest
from scriptworker.context import Context

import jinja2


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


def get_fake_valid_config():
    return load_json(path="beetmoverscript/test/fake_config.json")


def get_fake_valid_task(taskjson='task.json'):
    return load_json(path="beetmoverscript/test/test_work_dir/{}".format(taskjson))


def get_fake_balrog_props_path():
    return "beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/balrog_props.json"


def get_fake_balrog_props():
    return load_json(path=get_fake_balrog_props_path())


def get_fake_checksums_manifest():
    return (
        "14f2d1cb999a8b42a3b6b671f7376c3e246daa65d108e2b8fe880f069601dc2b26afa155b52001235db059 sha512 618149 firefox-53.0a1.en-US.linux-i686.complete.mar\n"
        "293975734953874539475 sha256 618149 firefox-53.0a1.en-US.linux-i686.complete.mar"
    )


@pytest.yield_fixture(scope='function')
def context():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.release_props = get_fake_balrog_props()['properties']
    context.release_props['platform'] = context.release_props['stage_platform']
    context.bucket = 'nightly'
    context.action = 'push-to-nightly'
    yield context


def get_test_jinja_env():
    return jinja2.Environment(loader=jinja2.PackageLoader("beetmoverscript.test"),
                              undefined=jinja2.StrictUndefined)
