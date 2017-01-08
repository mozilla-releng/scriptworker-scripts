from beetmoverscript.utils import load_json


def get_fake_valid_config():
    return load_json(path="beetmoverscript/test/fake_config.json")


def get_fake_valid_task():
    return load_json(path="beetmoverscript/test/test_work_dir/task.json")


def get_fake_balrog_props():
    return load_json(path="beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/balrog_props.json")


def get_fake_balrog_manifest():
    return load_json(path="beetmoverscript/test/fake_balrog_manifest.json")
