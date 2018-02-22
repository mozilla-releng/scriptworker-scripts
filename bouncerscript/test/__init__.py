import pytest

from scriptworker.context import Context
from bouncerscript.utils import load_json


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
