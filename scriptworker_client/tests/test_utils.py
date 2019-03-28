#!/usr/bin/env python
# coding=utf-8
"""Test scriptworker_client.utils
"""
import aiohttp
import asyncio
from asyncio.subprocess import PIPE
from async_generator import asynccontextmanager
from datetime import datetime
import mock
import os
import pytest
import re
import shutil
import subprocess
import tempfile
import time
import scriptworker_client.utils as utils
from scriptworker_client.exceptions import RetryError, TaskError, TimeoutError


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
    """Exercise ``load_json_or_yaml`` various options.

    """
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
    """``get_artifact_path`` gives the expected path.

    """
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
    """``pipe_to_log`` writes command output to the log filehandle.

    """
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
    """``get_log_filehandle`` gives a writable filehandle.

    """
    if path:
        path = os.path.join(tmpdir, path)
    with utils.get_log_filehandle(log_path=path) as log_fh:
        log_fh.write("foo")
    if path:
        with open(path) as fh:
            assert fh.read() == "foo"


# run_command {{{1
@pytest.mark.parametrize(
    "command, status, expected_log, exception, raises",
    (
        (
            ["bash", "-c", ">&2 echo bar && echo foo && exit 1"],
            1,
            ["foo\nbar\n", "bar\nfoo\n"],
            None,
            False,
        ),
        (
            ["bash", "-c", ">&2 echo bar && echo foo && exit 1"],
            1,
            ["foo\nbar\n", "bar\nfoo\n"],
            TaskError,
            True,
        ),
    ),
)
@pytest.mark.asyncio
async def test_run_command(command, status, expected_log, exception, raises, tmpdir):
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
                command, log_path=log_path, cwd=tmpdir, exception=exception
            )
    else:
        assert (
            await utils.run_command(
                command, log_path=log_path, cwd=tmpdir, exception=exception
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
