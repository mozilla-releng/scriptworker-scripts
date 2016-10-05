from beetmoverscript.test import get_fake_valid_task, get_fake_valid_config
from beetmoverscript.task import validate_task_schema
from scriptworker.context import Context


def test_validate_task():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    validate_task_schema(context)
