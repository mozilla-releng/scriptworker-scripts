import pytest
from scriptworker.context import Context

from . import get_fake_valid_config, get_fake_valid_task


@pytest.yield_fixture(scope="function")
def context():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.release_props = context.task["payload"]["releaseProperties"]
    context.release_props["stage_platform"] = context.release_props["platform"]

    context.bucket = "nightly"
    context.action = "push-to-nightly"
    yield context
