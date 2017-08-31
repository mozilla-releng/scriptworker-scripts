from beetmoverscript.utils import load_json


def get_fake_valid_config():
    return load_json(path="beetmoverscript/test/fake_config.json")


def get_fake_valid_task(taskjson='task.json'):
    return load_json(path="beetmoverscript/test/test_work_dir/{}".format(taskjson))


def get_fake_balrog_props():
    return load_json(path="beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/balrog_props.json")


def get_fake_checksums_manifest():
    return (
        "14f2d1cb999a8b42a3b6b671f7376c3e246daa65d108e2b8fe880f069601dc2b26afa155b52001235db059 sha512 618149 firefox-53.0a1.en-US.linux-i686.complete.mar\n"
        "293975734953874539475 sha256 618149 firefox-53.0a1.en-US.linux-i686.complete.mar"
    )
