import jinja2
from beetmoverscript.utils import load_json


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


def get_fake_valid_config():
    config = {
        'release_schema_file': 'src/beetmoverscript/data/release_beetmover_task_schema.json',
        'schema_file': 'src/beetmoverscript/data/beetmover_task_schema.json',
        'maven_schema_file': 'src/beetmoverscript/data/maven_beetmover_task_schema.json',
    }
    config.update(load_json(path="tests/fake_config.json"))
    return config


def get_fake_valid_task(taskjson='task.json'):
    return load_json(path="tests/test_work_dir/{}".format(taskjson))


def get_fake_checksums_manifest():
    return (
        "14f2d1cb999a8b42a3b6b671f7376c3e246daa65d108e2b8fe880f069601dc2b26afa155b52001235db059 sha512 618149 firefox-53.0a1.en-US.linux-i686.complete.mar\n"
        "293975734953874539475 sha256 618149 firefox-53.0a1.en-US.linux-i686.complete.mar"
    )


def get_test_jinja_env():
    return jinja2.Environment(loader=jinja2.PackageLoader("tests"),
                              undefined=jinja2.StrictUndefined)
