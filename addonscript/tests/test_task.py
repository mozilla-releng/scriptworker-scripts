import os

import pytest
from scriptworker.context import Context
from scriptworker.exceptions import TaskVerificationError

import addonscript.task as task


@pytest.fixture(scope="function")
def context(tmpdir):
    context = Context()
    context.config = {
        "taskcluster_scope_prefix": "project:releng:addons.mozilla.org:server",
        "amo_instances": {
            "project:releng:addons.mozilla.org:server:dev": {"amo_server": "http://some-amo-it.url", "jwt_user": "some-username", "jwt_secret": "some-secret"}
        },
        "work_dir": tmpdir,
    }
    context.task = {
        "dependencies": ["someTaskId"],
        "payload": {"release_name": "Firefox-59.0b3-build1"},
        "scopes": ["project:releng:addons.mozilla.org:server:dev"],
    }

    return context


@pytest.fixture(scope="function", params=(("unlisted", ("en-US", "en-GB")), ("listed", ("de", "ja", "ja-JP-mac"))), ids=("unlisted", "listed"))
async def task_dfn(request):
    channel, locales = request.param
    payload = {"channel": channel, "upstreamArtifacts": []}
    i = 0
    for locale in locales:
        i += 1
        payload["upstreamArtifacts"].append(
            {"paths": ["public/build/{}/target.langpack.xpi".format(locale)], "taskId": "UPSTREAM{}".format(i), "taskType": "build"}
        )
    return {
        "provisionerId": "meh",
        "workerType": "workertype",
        "schedulerId": "task-graph-scheduler",
        "taskGroupId": "some",
        "routes": [],
        "retries": 5,
        "created": "2015-05-08T16:15:58.903Z",
        "deadline": "2015-05-08T18:15:59.010Z",
        "expires": "2016-05-08T18:15:59.010Z",
        "dependencies": ["UPSTREAM{}".format(n + 1) for n in range(i)],
        "scopes": [],
        "payload": payload,
        "metadata": {"source": "https://hg.mozilla.org/releases/mozilla-test-source" "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }


def test_get_channel(task_dfn):
    channel = task_dfn["payload"]["channel"]
    assert channel == task.get_channel(task_dfn)


def test_get_channel_missing(task_dfn):
    del task_dfn["payload"]["channel"]
    with pytest.raises(TaskVerificationError):
        task.get_channel(task_dfn)


def test_build_filelist(context, task_dfn):
    expected_paths = set()
    for a in task_dfn["payload"]["upstreamArtifacts"]:
        abs_path = os.path.join(context.config["work_dir"], "cot", a["taskId"], a["paths"][0])
        expected_paths.add(abs_path)
        os.makedirs(os.path.dirname(abs_path))
        with open(abs_path, "w") as f:
            # Make file exist
            print("something", file=f)
    context.task = task_dfn
    file_list = task.build_filelist(context)
    assert len(file_list) == len(task_dfn["payload"]["upstreamArtifacts"])
    assert expected_paths == set(file_list)
    assert isinstance(file_list, type([]))


def test_build_filelist_missing_file(context, task_dfn):
    expected_paths = set()
    for a in task_dfn["payload"]["upstreamArtifacts"]:
        abs_path = os.path.join(context.config["work_dir"], "cot", a["taskId"], a["paths"][0])
        expected_paths.add(abs_path)
        os.makedirs(os.path.dirname(abs_path))
        with open(abs_path, "w") as f:
            # Make file exist
            print("something", file=f)
    task_dfn["payload"]["upstreamArtifacts"][-1]["taskId"] = "MISSINGTASK"
    context.task = task_dfn
    with pytest.raises(TaskVerificationError):
        task.build_filelist(context)


@pytest.mark.parametrize(
    "api_root, scope",
    (
        ("http://localhost:5000", "project:releng:addons.mozilla.org:server:dev"),
        ("http://some-amo.url", "project:releng:addons.mozilla.org:server:dev"),
        ("https://addons.allizom.org", "project:releng:addons.mozilla.org:server:staging"),
        ("https://addons.allizom.org/", "project:releng:addons.mozilla.org:server:staging"),
        ("https://addons.mozilla.org", "project:releng:addons.mozilla.org:server:production"),
        ("https://addons.mozilla.org/", "project:releng:addons.mozilla.org:server:production"),
    ),
)
def test_get_amo_instance_config_from_scope(context, api_root, scope):
    context.config["amo_instances"][scope] = context.config["amo_instances"]["project:releng:addons.mozilla.org:server:dev"]
    context.config["amo_instances"][scope]["amo_server"] = api_root
    context.task["scopes"] = [scope]

    assert task.get_amo_instance_config_from_scope(context) == {"amo_server": api_root, "jwt_user": "some-username", "jwt_secret": "some-secret"}


@pytest.mark.parametrize(
    "scope", ("some:random:scope", "project:releng:addons.mozilla.org:server:staging", "project:releng:addons.mozilla.org:server:production")
)
def test_fail_get_amo_instance_config_from_scope(context, scope):
    context.task["scopes"] = [scope]
    with pytest.raises(TaskVerificationError):
        task.get_amo_instance_config_from_scope(context)


@pytest.mark.parametrize(
    "scopes, raises",
    (
        (("project:releng:addons.mozilla.org:server:dev",), False),
        (("project:releng:addons.mozilla.org:server:staging",), False),
        (("project:releng:addons.mozilla.org:server:production",), False),
        (("project:releng:addons.mozilla.org:server:dev", "project:releng:addons.mozilla.org:server:production"), True),
        (("some:random:scope",), True),
    ),
)
def test_get_scope(context, scopes, raises):
    context.task["scopes"] = scopes

    if raises:
        with pytest.raises(TaskVerificationError):
            task._get_scope(context)
    else:
        assert task._get_scope(context) == scopes[0]
