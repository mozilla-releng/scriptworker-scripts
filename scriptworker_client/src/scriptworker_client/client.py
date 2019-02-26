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
from urllib.parse import unquote

from scriptworker_client.constants import STATUSES
from scriptworker_client.exceptions import ClientError, TaskError, TaskVerificationError
from scriptworker_client.utils import load_json_or_yaml, match_url_regex

log = logging.getLogger(__name__)


def get_task(config):
    """Read the task.json from work_dir.

    Args:
        config (dict): the running config, to find work_dir.

    Returns:
        dict: the contents of task.json

    Raises:
        TaskError: on error.

    """
    path = os.path.join(config['work_dir'], "task.json")
    message = "Can't read task from {}!\n%(exc)s".format(path)
    contents = load_json_or_yaml(path, is_path=True, message=message)
    return contents


def validate_json_schema(data, schema, name="task"):
    """Given data and a jsonschema, let's validate it.

    This happens for tasks and chain of trust artifacts.

    Args:
        data (dict): the json to validate.
        schema (dict): the jsonschema to validate against.
        name (str, optional): the name of the json, for exception messages.
            Defaults to "task".

    Raises:
        TaskError: on failure

    """
    try:
        jsonschema.validate(data, schema)
    except jsonschema.exceptions.ValidationError as exc:
        raise TaskError(
            "Can't validate {} schema!\n{}".format(name, str(exc)),
            exit_code=STATUSES['malformed-payload']
        )


def validate_task_schema(config, task, schema_key='schema_file'):
    """Validate the task definition.

    Args:
        config (dict): the running config
        task (dict): the running task
        schema_key: the key in `config` where the path to the schema file is. Key can contain
            dots (e.g.: 'schema_files.file_a')

    Raises:
        TaskVerificationError: if the task doesn't match the schema

    """
    schema_path = config
    schema_keys = schema_key.split('.')
    try:
        for key in schema_keys:
            schema_path = schema_path[key]

        task_schema = load_json_or_yaml(schema_path, is_path=True)
        log.debug('Task is validated against this schema: {}'.format(task_schema))

        validate_json_schema(task, task_schema)
    except (KeyError, TaskError) as e:
        raise TaskVerificationError('Cannot validate task against schema. Task: {}.'.format(task)) from e


def validate_artifact_url(valid_artifact_rules, valid_artifact_task_ids, url):
    """Ensure a URL fits in given scheme, netloc, and path restrictions.

    If we fail any checks, raise a TaskError with
    ``malformed-payload``.

    Args:
        valid_artifact_rules (tuple): the tests to run, with ``schemas``, ``netlocs``,
            and ``path_regexes``.
        valid_artifact_task_ids (list): the list of valid task IDs to download from.
        url (str): the url of the artifact.

    Returns:
        str: the ``filepath`` of the path regex.

    Raises:
        TaskError: on failure to validate.

    """
    def callback(match):
        path_info = match.groupdict()
        # make sure we're pointing at a valid task ID
        if 'taskId' in path_info and \
                path_info['taskId'] not in valid_artifact_task_ids:
            return
        if 'filepath' not in path_info:
            return
        return path_info['filepath']

    filepath = match_url_regex(valid_artifact_rules, url, callback)
    if filepath is None:
        raise TaskError(
            "Can't validate url {}".format(url),
            exit_code=STATUSES['malformed-payload']
        )
    return unquote(filepath).lstrip('/')


def sync_main(async_main, config_path=None, default_config=None,
              should_validate_task=True, loop_function=asyncio.get_event_loop):
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
        should_validate_task (bool, optional): whether we should validate the task
            schema. Defaults to True.
        loop_function (function, optional): the function to call to get the
            event loop; here for testing purposes. Defaults to
            ``asyncio.get_event_loop``.

    """
    config = _init_config(config_path, default_config)
    _init_logging(config)
    task = get_task(config)
    if should_validate_task:
        validate_task_schema(config, task)
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
    print('Usage: {} CONFIG_FILE'.format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def _init_logging(config):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG if config.get('verbose') else logging.INFO
    )
    logging.getLogger('taskcluster').setLevel(logging.WARNING)


async def _handle_asyncio_loop(async_main, config, task):
    try:
        await async_main(config, task)
    except ClientError as exc:
        log.exception("Failed to run async_main")
        sys.exit(exc.exit_code)
