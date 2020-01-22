import json
import os

from scriptworker.exceptions import ScriptWorkerTaskException

import bouncerscript


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
    data_dir = os.path.join(os.path.dirname(bouncerscript.__file__), "data")
    config = {
        "schema_files": {
            "submission": os.path.join(data_dir, "bouncer_submission_task_schema.json"),
            "aliases": os.path.join(data_dir, "bouncer_aliases_task_schema.json"),
            "locations": os.path.join(data_dir, "bouncer_locations_task_schema.json"),
        }
    }
    config.update(load_json(path="tests/fake_config.json"))
    return config


def get_fake_valid_task(jobtype):
    return load_json(path="tests/test_work_dir/task_{}.json".format(jobtype))


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)
