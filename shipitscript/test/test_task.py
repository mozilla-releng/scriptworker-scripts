from scriptworker.context import Context

from shipitscript.script import get_default_config
from shipitscript.task import validate_task_schema


def test_validate_task():
    context = Context()
    context.config = get_default_config()
    context.task = {}
    validate_task_schema(context)
