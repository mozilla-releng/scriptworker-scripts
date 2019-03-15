#!/usr/bin/env python
# coding=utf-8
"""Test scriptworker_client.client
"""
from copy import deepcopy
import json
import logging
import mock
import os
import pytest
import sys
import tempfile
import scriptworker_client.client as client
from scriptworker_client.exceptions import TaskError, TaskVerificationError


# helpers {{{1

FAKE_SCHEMA = {
    "title": "foo",
    "type": "object",
    "properties": {
        "list-of-strings": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
            }
        },
    },
    "required": ["list-of-strings"],
}

# get_task {{{1
def test_get_task():
    """Get the contents of ``work_dir/task.json``.

    """
    expected = {'foo': 'bar'}
    with tempfile.TemporaryDirectory() as tmp:
        config = {'work_dir': tmp}
        with open(os.path.join(tmp, 'task.json'), 'w') as fh:
            fh.write(json.dumps(expected))
        assert client.get_task(config) == expected


# verify_json_schema {{{1
@pytest.mark.parametrize('data,schema,raises', ((
    {
        "list-of-strings": ['a', 'b'],
    },
    FAKE_SCHEMA,
    False
), (
    {
        "list-of-strings": ['a', 'a'],
    },
    FAKE_SCHEMA,
    True
), (
    {
        "list-of-strings": [],
    },
    FAKE_SCHEMA,
    True
), (
    {
        "list-of-strings": {"foo": "bar"},
    },
    FAKE_SCHEMA,
    True
), (
    {
        "invalid-key": {},
    },
    FAKE_SCHEMA,
    True
)))
def test_verify_json_schema(data, schema, raises):
    """``verify_json_schema`` raises if the data doesn't verify against the schema.

    """
    if raises:
        with pytest.raises(TaskVerificationError):
            client.verify_json_schema(data, schema)
    else:
        client.verify_json_schema(data, schema)


# verify_task_schema {{{1
def test_verify_task_schema():
    """``verify_task_schema`` raises if the task doesn't match the schema.

    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "schema.json")
        with open(path, 'w') as fh:
            fh.write(json.dumps(FAKE_SCHEMA))
        config = {
            "foo": {
                "bar": path
            },
        }
        client.verify_task_schema(config, {"list-of-strings": ["a"]}, "foo.bar")
        with pytest.raises(TaskVerificationError):
            client.verify_task_schema(config, {"list-of-strings": ["a", "a"]}, "foo.bar")
        with pytest.raises(TaskVerificationError):
            client.verify_task_schema(config, {"list-of-strings": ["a", "a"]}, "nonexistent_path")


@pytest.mark.asyncio
@pytest.mark.parametrize('should_verify_task', (True, False))
async def test_sync_main_runs_fully(should_verify_task):
    """``sync_main`` runs fully.

    """
    with tempfile.TemporaryDirectory() as work_dir:
        config = {
            'work_dir': work_dir,
            'schema_file': os.path.join(
                os.path.dirname(__file__), 'data', 'basic_schema.json'
            ),
        }
        with open(os.path.join(config['work_dir'], 'task.json'), "w") as fh:
            fh.write(json.dumps({
                "this_is_a_task": True,
                "payload": {
                    "payload_required_property": "..."
                }
            }))
        async_main_calls = []
        run_until_complete_calls = []

        async def async_main(*args):
            async_main_calls.append(args)

        def count_run_until_complete(arg1):
            run_until_complete_calls.append(arg1)

        fake_loop = mock.MagicMock()
        fake_loop.run_until_complete = count_run_until_complete

        def loop_function():
            return fake_loop

        kwargs = {'loop_function': loop_function}

        if not should_verify_task:
            kwargs['should_verify_task'] = False

        with tempfile.NamedTemporaryFile('w+') as f:
            json.dump(config, f)
            f.seek(0)

            kwargs['config_path'] = f.name
            client.sync_main(async_main, **kwargs)

        for i in run_until_complete_calls:
            await i  # suppress coroutine not awaited warning
        assert len(run_until_complete_calls) == 1  # run_until_complete was called once
        assert len(async_main_calls) == 1  # async_main was called once


def test_usage(capsys, monkeypatch):
    """``_usage`` prints the expected error and exits.

    """
    monkeypatch.setattr(sys, 'argv', ['my_binary'])
    with pytest.raises(SystemExit):
        client._usage()

    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == 'Usage: my_binary CONFIG_FILE\n'


@pytest.mark.parametrize('is_verbose, log_level', (
    (True, logging.DEBUG),
    (False, logging.INFO),
))
def test_init_logging(monkeypatch, is_verbose, log_level):
    """``_init_logging`` sets the logging module format and level.

    """
    basic_config_mock = mock.MagicMock()
    config = {'verbose': is_verbose}

    monkeypatch.setattr(logging, 'basicConfig', basic_config_mock)
    client._init_logging(config)

    basic_config_mock.assert_called_once_with(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=log_level,
    )
    assert logging.getLogger('taskcluster').level == logging.WARNING


@pytest.mark.asyncio
async def test_handle_asyncio_loop():
    """``_handle_asyncio_loop`` calls ``async_main``.

    """
    config = {}

    async def async_main(*args, **kwargs):
        config['was_async_main_called'] = True

    await client._handle_asyncio_loop(async_main, config, {})

    assert config.get('was_async_main_called')


@pytest.mark.asyncio
async def test_fail_handle_asyncio_loop(mocker):
    """``_handle_asyncio_loop`` exits properly on failure.

    """
    m = mocker.patch.object(client, "log")

    async def async_error(*args, **kwargs):
        exception = TaskError('async_error!')
        exception.exit_code = 42
        raise exception

    with pytest.raises(SystemExit) as excinfo:
        await client._handle_asyncio_loop(async_error, {}, {})

    assert excinfo.value.code == 42
    m.exception.assert_called_once_with("Failed to run async_main")


def test_init_config_cli(mocker):
    """_init_config can get its config from the commandline if not specified.

    """
    mocker.patch.object(sys, 'argv', new=['x'])
    with pytest.raises(SystemExit):
        client._init_config()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'foo.json')
        config = {'a': 'b'}
        default_config = {'c': 'd'}
        with open(path, 'w') as fh:
            fh.write(json.dumps(config))
        expected = deepcopy(default_config)
        expected.update(config)
        mocker.patch.object(sys, 'argv', new=['x', path])
        assert client._init_config(default_config=default_config) == expected
