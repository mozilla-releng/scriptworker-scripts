#!/usr/bin/env python
# coding=utf-8
"""Test scriptworker_client.utils
"""
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from asyncio.subprocess import PIPE
from datetime import datetime

import aiohttp
import mock
import pytest

import scriptworker_client.utils as utils
from scriptworker_client.exceptions import ClientError, RetryError, TaskError

if sys.version_info < (3, 7):
    from async_generator import asynccontextmanager
else:
    from contextlib import asynccontextmanager


retry_count = {}


async def fail_first(*args, **kwargs):
    global retry_count
    retry_count["fail_first"] += 1
    if retry_count["fail_first"] < 2:
        raise RetryError("first")
    return "yay"


async def always_fail(*args, **kwargs):
    global retry_count
    retry_count.setdefault("always_fail", 0)
    retry_count["always_fail"] += 1
    raise ClientError("fail")


async def fake_sleep(*args, **kwargs):
    pass


# helpers {{{1
# from https://github.com/SecurityInnovation/PGPy/blob/develop/tests/test_01_types.py
text = {  # some basic utf-8 test strings - these should all pass             'english': u'The quick brown fox jumped over the lazy dog',
    # this hiragana pangram comes from http://www.columbia.edu/~fdc/utf8/
    "hiragana": u"いろはにほへど　ちりぬるを\n"
    u"わがよたれぞ　つねならむ\n"
    u"うゐのおくやま　けふこえて\n"
    u"あさきゆめみじ　ゑひもせず",
    "poo": u"Hello, \U0001F4A9!",
}

non_text = {
    "None": None,
    "dict": {"a": 1, 2: 3},
    "cyrillic": u"грызть гранит науки".encode("iso8859_5"),
    "cp865": u"Mit luftpudefartøj er fyldt med ål".encode("cp865"),
}


# load_json_or_yaml {{{1
@pytest.mark.parametrize(
    "string,is_path,exception,raises,result",
    (
        (
            os.path.join(os.path.dirname(__file__), "data", "bad.json"),
            True,
            None,
            False,
            {"credentials": ["blah"]},
        ),
        ('{"a": "b"}', False, None, False, {"a": "b"}),
        ('{"a": "b}', False, None, False, None),
        ('{"a": "b}', False, TaskError, True, None),
    ),
)
def test_load_json_or_yaml(string, is_path, exception, raises, result):
    """Exercise ``load_json_or_yaml`` various options."""
    if raises:
        with pytest.raises(exception):
            utils.load_json_or_yaml(string, is_path=is_path, exception=exception)
    else:
        for file_type in ("json", "yaml"):
            assert result == utils.load_json_or_yaml(
                string, is_path=is_path, exception=exception, file_type=file_type
            )


# get_artifact_path {{{1
@pytest.mark.parametrize(
    "work_dir, expected",
    ((None, "cot/taskId/public/foo"), ("work_dir", "work_dir/cot/taskId/public/foo")),
)
def test_get_artifact_path(work_dir, expected):
    """``get_artifact_path`` gives the expected path."""
    assert (
        utils.get_artifact_path("taskId", "public/foo", work_dir=work_dir) == expected
    )


# to_unicode {{{1
@pytest.mark.parametrize(
    "input, expected",
    [[v, v] for _, v in sorted(text.items())]
    + [[v, v] for _, v in sorted(non_text.items())]
    + [[b"foo", "foo"]],
)
def test_to_unicode(input, expected):
    """``to_unicode`` returns unicode, given unicode or bytestring input. Otherwise
    it returns the input unchanged.

    """
    assert utils.to_unicode(input) == expected


# pipe_to_log {{{1
@pytest.mark.asyncio
async def test_pipe_to_log(tmpdir):
    """``pipe_to_log`` writes command output to the log filehandle."""
    cmd = r""">&2 echo "foo" && echo "bar" && exit 0"""
    proc = await asyncio.create_subprocess_exec(
        "bash", "-c", cmd, stdout=PIPE, stderr=PIPE, stdin=None
    )
    tasks = []
    path = os.path.join(tmpdir, "log")
    with open(path, "w") as log_fh:
        tasks.append(utils.pipe_to_log(proc.stderr, filehandles=[log_fh]))
        tasks.append(utils.pipe_to_log(proc.stdout, filehandles=[log_fh]))
        await asyncio.wait(tasks)
        await proc.wait()
    with open(path, "r") as fh:
        assert fh.read() in ("foo\nbar\n", "bar\nfoo\n")


# get_log_filehandle {{{1
@pytest.mark.parametrize("path", (None, "log"))
def test_get_log_filehandle(path, tmpdir):
    """``get_log_filehandle`` gives a writable filehandle."""
    if path:
        path = os.path.join(tmpdir, path)
    with utils.get_log_filehandle(log_path=path) as log_fh:
        log_fh.write("foo")
    if path:
        with open(path) as fh:
            assert fh.read() == "foo"


# run_command {{{1
@pytest.mark.parametrize(
    "command, status, expected_log, exception, output_log, env, raises",
    (
        (
            ["bash", "-c", ">&2 echo bar && echo foo && exit 1"],
            1,
            ["foo\nbar\n", "bar\nfoo\n"],
            None,
            False,
            None,
            False,
        ),
        (
            ["bash", "-c", ">&2 echo bar && echo foo && exit 1"],
            1,
            ["foo\nbar\n", "bar\nfoo\n"],
            TaskError,
            False,
            {"foo": "bar"},
            True,
        ),
        (
            ["bash", "-c", ">&2 echo bar && echo foo && exit 1"],
            1,
            ["foo\nbar\n", "bar\nfoo\n"],
            TaskError,
            True,
            None,
            True,
        ),
    ),
)
@pytest.mark.asyncio
async def test_run_command(
    command, status, expected_log, exception, output_log, env, raises, tmpdir
):
    """``run_command`` runs the expected command, logs its output, and exits
    with its exit status. If ``exception`` is set and we exit non-zero, we
    raise that exception.

    """
    if not isinstance(expected_log, list):
        expected_log = [expected_log]
    log_path = os.path.join(tmpdir, "log")
    if raises:
        with pytest.raises(exception):
            await utils.run_command(
                command,
                log_path=log_path,
                cwd=tmpdir,
                env=env,
                exception=exception,
                output_log_on_exception=output_log,
            )
    else:
        assert (
            await utils.run_command(
                command,
                log_path=log_path,
                cwd=tmpdir,
                env=env,
                exception=exception,
                output_log_on_exception=output_log,
            )
            == status
        )
        with open(log_path, "r") as fh:
            assert fh.read() in expected_log


# list_files {{{1
def test_list_files():
    """``list_files`` yields a list of all files in a directory, ignoring
    ``ignored_list``.

    """
    parent_dir = os.path.dirname(__file__)
    ignored = os.path.join(parent_dir, "data", "bad.json")
    output = subprocess.check_output(
        ["find", parent_dir, "-type", "f", "-print"]
    ).decode("utf-8")
    expected_paths = output.splitlines()
    all_paths = []
    paths_with_ignore = []
    for path in utils.list_files(parent_dir):
        all_paths.append(path)
    for path in utils.list_files(parent_dir, ignore_list=["bad.json"]):
        paths_with_ignore.append(path)

    assert set(all_paths + [ignored]) == set(expected_paths)
    assert set(expected_paths) - set(paths_with_ignore) == {ignored}


# makedirs {{{1
@pytest.mark.parametrize(
    "path, raises",
    (
        (None, False),
        (os.path.join(os.path.dirname(__file__), "data", "bad.json"), True),
        (os.path.join(os.path.dirname(__file__), "data", "bad.json", "bar"), True),
        (os.path.dirname(__file__), False),
        ("%s/foo/bar/baz", False),
    ),
)
def test_makedirs(path, raises, tmpdir):
    """``makedirs`` creates ``path`` and all missing parent directories if it is a
    nonexistent directory. If ``path`` is ``None``, it is noop. And if ``path``
    is an existing file, it raises ``TaskError``.

    """
    if raises:
        with pytest.raises(TaskError):
            utils.makedirs(path)
    else:
        if path and "%s" in path:
            path = path % tmpdir
        utils.makedirs(path)
        if path:
            assert os.path.isdir(path)


# rm {{{1
def test_rm_empty():
    utils.rm(None)


def test_rm_file():
    _, tmp = tempfile.mkstemp()
    assert os.path.exists(tmp)
    utils.rm(tmp)
    assert not os.path.exists(tmp)


def test_rm_dir(tmpdir):
    assert os.path.exists(tmpdir)
    utils.rm(tmpdir)
    assert not os.path.exists(tmpdir)


@pytest.mark.parametrize("attempt", (-1, 0))
def test_calculate_no_sleep_time(attempt):
    assert utils.calculate_sleep_time(attempt) == 0


@pytest.mark.parametrize(
    "attempt,kwargs,min_expected,max_expected",
    (
        (
            1,
            {"delay_factor": 5.0, "randomization_factor": 0, "max_delay": 15},
            5.0,
            5.0,
        ),
        (
            2,
            {"delay_factor": 5.0, "randomization_factor": 0.25, "max_delay": 15},
            10.0,
            12.5,
        ),
        (
            3,
            {"delay_factor": 5.0, "randomization_factor": 0.25, "max_delay": 10},
            10.0,
            10.0,
        ),
    ),
)
def test_calculate_sleep_time(attempt, kwargs, min_expected, max_expected):
    assert min_expected <= utils.calculate_sleep_time(attempt, **kwargs) <= max_expected


@pytest.mark.asyncio
async def test_retry_async_fail_first():
    global retry_count
    retry_count["fail_first"] = 0
    status = await utils.retry_async(fail_first, sleeptime_kwargs={"delay_factor": 0})
    assert status == "yay"
    assert retry_count["fail_first"] == 2


@pytest.mark.asyncio
async def test_retry_async_always_fail():
    global retry_count
    retry_count["always_fail"] = 0
    with mock.patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises(ClientError):
            status = await utils.retry_async(
                always_fail, sleeptime_kwargs={"delay_factor": 0}
            )
            assert status is None
    assert retry_count["always_fail"] == 5


@pytest.mark.asyncio
async def test_retry_async_decorator_fail_first():
    global retry_count

    @utils.retry_async_decorator(sleeptime_kwargs={"delay_factor": 0})
    async def decorated_fail_first(*args, **kwargs):
        return await fail_first(*args, **kwargs)

    retry_count["fail_first"] = 0
    status = await decorated_fail_first()
    assert status == "yay"
    assert retry_count["fail_first"] == 2


@pytest.mark.asyncio
async def test_retry_async_decorator_always_fail_async():
    global retry_count

    @utils.retry_async_decorator(sleeptime_kwargs={"delay_factor": 0})
    async def decorated_always_fail(*args, **kwargs):
        return await always_fail(*args, **kwargs)

    retry_count["always_fail"] = 0
    with mock.patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises(ClientError):
            await decorated_always_fail()

    assert retry_count["always_fail"] == 5


@pytest.mark.asyncio
async def test_retry_async_decorator_always_fail_async():
    global retry_count

    @utils.retry_async_decorator(sleeptime_kwargs={"delay_factor": 0})
    async def decorated_always_fail(*args, **kwargs):
        return await always_fail(*args, **kwargs)

    retry_count["always_fail"] = 0
    with mock.patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises(ClientError):
            await decorated_always_fail()

    assert retry_count["always_fail"] == 5


@pytest.mark.asyncio
async def test_async_wrap():
    # Based on https://dev.to/0xbf/turn-sync-function-to-async-python-tips-58nn
    async_sleep = utils.async_wrap(time.sleep)

    start_time = time.time()
    await asyncio.gather(async_sleep(0.1), async_sleep(0.1), async_sleep(0.1))
    elapsed_time = time.time() - start_time

    assert 0.0 <= elapsed_time <= 0.2


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", (IOError, SyntaxError, None))
async def test_raise_future_exceptions(exc):
    async def one():
        if exc is not None:
            raise exc("foo")

    async def two():
        pass

    tasks = [asyncio.ensure_future(one()), asyncio.ensure_future(two())]
    if exc is not None:
        with pytest.raises(exc):
            await utils.raise_future_exceptions(tasks)
    else:
        await utils.raise_future_exceptions(tasks)


@pytest.mark.parametrize(
    "url, expected",
    (
        ("https://foo/bar", ["bar"]),
        ("https://foo/bar/baz", ["bar", "baz"]),
        ("https://foo/bar/baz?param1=value", ["bar", "baz"]),
        ("https://foo/bar/baz?param1=value1&param2=value2", ["bar", "baz"]),
    ),
)
def test_get_parts_of_url_path(url, expected):
    assert utils.get_parts_of_url_path(url) == expected


@pytest.mark.asyncio
async def test_raise_future_exceptions_noop():
    await utils.raise_future_exceptions([])


@pytest.mark.parametrize(
    "sequence, condition, expected",
    (
        (["a", "b", "c"], lambda item: item == "b", "b"),
        (
            ({"some_key": 1}, {"some_key": 2}, {"some_key": 3}),
            lambda item: item["some_key"] == 1,
            {"some_key": 1},
        ),
        (range(1, 10), lambda item: item == 5, 5),
        ({"a": 1, "b": 2, "c": 3}.keys(), lambda item: item == "b", "b"),
        ({"a": 1, "b": 2, "c": 3}.values(), lambda item: item == 2, 2),
    ),
)
def test_get_single_item_from_sequence(sequence, condition, expected):
    assert utils.get_single_item_from_sequence(sequence, condition) == expected


class SomeCustomError(Exception):
    pass


@pytest.mark.parametrize(
    "list_, condition, ErrorClass, no_item_error_message, too_many_item_error_message, append_list_to_error_message, \
 has_all_params, expected_message",
    (
        (
            ["a", "b", "c"],
            lambda item: item == "z",
            SomeCustomError,
            "NO ITEM",
            "TOO MANY",
            True,
            True,
            "NO ITEM. Given: ['a', 'b', 'c']",
        ),
        (
            ["a", "b", "c"],
            lambda item: item == "z",
            SomeCustomError,
            "NO ITEM",
            "TOO MANY",
            False,
            True,
            "NO ITEM",
        ),
        (
            ["a", "b", "b"],
            lambda item: item == "b",
            SomeCustomError,
            "NO ITEM",
            "TOO MANY",
            True,
            True,
            "TOO MANY. Given: ['a', 'b', 'b']",
        ),
        (
            ["a", "b", "c"],
            lambda _: False,
            ValueError,
            None,
            None,
            None,
            False,
            "No item matched condition. Given: ['a', 'b', 'c']",
        ),
        (
            ["a", "b", "c"],
            lambda _: True,
            ValueError,
            None,
            None,
            None,
            False,
            "Too many items matched condition. Given: ['a', 'b', 'c']",
        ),
    ),
)
def test_fail_get_single_item_from_sequence(
    list_,
    condition,
    ErrorClass,
    no_item_error_message,
    too_many_item_error_message,
    append_list_to_error_message,
    has_all_params,
    expected_message,
):
    with pytest.raises(ErrorClass) as exec_info:
        if has_all_params:
            utils.get_single_item_from_sequence(
                list_,
                condition,
                ErrorClass,
                no_item_error_message,
                too_many_item_error_message,
                append_list_to_error_message,
            )
        else:
            utils.get_single_item_from_sequence(list_, condition)

    assert str(exec_info.value) == expected_message
