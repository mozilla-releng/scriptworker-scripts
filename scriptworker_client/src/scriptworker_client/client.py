#!/usr/bin/env python
"""Python3 scripts running in scriptworker will use functions in this file.

Attributes:
    log (logging.Logger): the log object for the module

"""
import asyncio
import jsonschema
import logging
import os
import sys

from scriptworker_client.exceptions import ClientError, TaskVerificationError
from scriptworker_client.utils import load_json_or_yaml

log = logging.getLogger(__name__)


def get_task(config):
    """Read the task.json from work_dir.

    Args:
        config (dict): the running config, to find work_dir.

    Returns:
        dict: the contents of task.json

    Raises:
        ClientError: on error.

    """
    path = os.path.join(config["work_dir"], "task.json")
    message = "Can't read task from {}!\n%(exc)s".format(path)
    contents = load_json_or_yaml(path, is_path=True, file_type='yaml', message=message)
    return contents


def verify_json_schema(data, schema, name="task"):
    """Given data and a jsonschema, let's verify it.

    This happens for tasks and chain of trust artifacts.

    Args:
        data (dict): the json to verify.
        schema (dict): the jsonschema to verify against.
        name (str, optional): the name of the json, for exception messages.
            Defaults to "task".

    Raises:
        TaskVerificationError: on failure

    """
    try:
        jsonschema.validate(data, schema)
    except jsonschema.exceptions.ValidationError as exc:
        raise TaskVerificationError(
            "Can't verify {} schema!\n{}".format(name, str(exc))
        ) from exc


def verify_task_schema(config, task, schema_key="schema_file"):
    """Verify the task definition.

    Args:
        config (dict): the running config
        task (dict): the running task
        schema_key: the key in `config` where the path to the schema file is. Key can contain
            dots (e.g.: 'schema_files.file_a')

    Raises:
        TaskVerificationError: if the task doesn't match the schema

    """
    schema_path = config
    schema_keys = schema_key.split(".")
    try:
        for key in schema_keys:
            schema_path = schema_path[key]

        task_schema = load_json_or_yaml(schema_path, is_path=True)
        log.debug("Task is verified against this schema: {}".format(task_schema))

        verify_json_schema(task, task_schema)
    except (KeyError, OSError) as e:
        raise TaskVerificationError(
            "Cannot verify task against schema. Task: {}.".format(task)
        ) from e


def sync_main(
    async_main,
    config_path=None,
    default_config=None,
    should_verify_task=True,
    loop_function=asyncio.get_event_loop,
):
    """Entry point for scripts using scriptworker.

    This function sets up the basic needs for a script to run. More specifically:
        * it initializes the config
        * the path to the config file is either taken from `config_path` or from `sys.argv[1]`.
        * it verifies `sys.argv` doesn't have more arguments than the config path.
        * it creates the asyncio event loop so that `async_main` can run

    Args:
        async_main (function): The function to call once everything is set up
        config_path (str, optional): The path to the file to load the config from.
            Loads from ``sys.argv[1]`` if ``None``. Defaults to None.
        default_config (dict, optional): the default config to use for ``_init_config``.
            defaults to None.
        should_verify_task (bool, optional): whether we should verify the task
            schema. Defaults to True.
        loop_function (function, optional): the function to call to get the
            event loop; here for testing purposes. Defaults to
            ``asyncio.get_event_loop``.

    """
    config = _init_config(config_path, default_config)
    _init_logging(config)
    task = get_task(config)
    if should_verify_task:
        verify_task_schema(config, task)
    loop = loop_function()
    loop.run_until_complete(_handle_asyncio_loop(async_main, config, task))


def _init_config(config_path=None, default_config=None):
    if config_path is None:
        if len(sys.argv) != 2:
            _usage()
        config_path = sys.argv[1]

    config = {} if default_config is None else default_config
    config.update(load_json_or_yaml(config_path, is_path=True))

    return config


def _usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def _init_logging(config):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if config.get("verbose") else logging.INFO,
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)


async def _handle_asyncio_loop(async_main, config, task):
    try:
        await async_main(config, task)
    except ClientError as exc:
        log.exception("Failed to run async_main")
        sys.exit(exc.exit_code)
