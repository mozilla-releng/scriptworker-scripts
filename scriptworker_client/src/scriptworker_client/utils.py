#!/usr/bin/env python
"""Generic utils for scriptworker-client.

Attributes:
    log (logging.Logger): the log object for the module

"""
import json
import logging
import re
from urllib.parse import unquote, urlparse
import yaml
from scriptworker_client.exceptions import TaskError

log = logging.getLogger(__name__)


# load_json_or_yaml {{{1
def load_json_or_yaml(string, is_path=False, file_type='json',
                      exception=TaskError,
                      message="Failed to load %(file_type)s: %(exc)s"):
    """Load json or yaml from a filehandle or string, and raise a custom exception on failure.

    Args:
        string (str): json/yaml body or a path to open
        is_path (bool, optional): if ``string`` is a path. Defaults to False.
        file_type (str, optional): either "json" or "yaml". Defaults to "json".
        exception (exception, optional): the exception to raise on failure.
            If None, don't raise an exception.  Defaults to TaskError.
        message (str, optional): the message to use for the exception.
            Defaults to "Failed to load %(file_type)s: %(exc)s"

    Returns:
        dict: the data from the string.

    Raises:
        Exception: as specified, on failure

    """
    if file_type == 'json':
        _load_fh = json.load
        _load_str = json.loads
    else:
        _load_fh = yaml.safe_load
        _load_str = yaml.safe_load

    try:
        if is_path:
            with open(string, 'r') as fh:
                contents = _load_fh(fh)
        else:
            contents = _load_str(string)
        return contents
    except (OSError, ValueError, yaml.scanner.ScannerError) as exc:
        if exception is not None:
            repl_dict = {'exc': str(exc), 'file_type': file_type}
            raise exception(message % repl_dict)


# match_url_path_callback {{{1
def match_url_path_callback(match):
    """Return the path, as a ``match_url_regex`` callback.

    Args:
        match (re.match): the regex match object from ``match_url_regex``

    Returns:
        string: the path matched in the regex.

    """
    path_info = match.groupdict()
    return path_info['path']


# match_url_regex {{{1
def match_url_regex(rules, url, callback):
    """Given rules and a callback, find the rule that matches the url.

    Rules look like::

        (
            {
                'schemes': ['https', 'ssh'],
                'netlocs': ['hg.mozilla.org'],
                'path_regexes': [
                    "^(?P<path>/mozilla-(central|unified))(/|$)",
                ]
            },
            ...
        )

    Args:
        rules (list): a list of dictionaries specifying lists of ``schemes``,
            ``netlocs``, and ``path_regexes``.
        url (str): the url to test
        callback (function): a callback that takes an ``re.MatchObject``.
            If it returns None, continue searching.  Otherwise, return the
            value from the callback.

    Returns:
        value: the value from the callback, or None if no match.

    """
    parts = urlparse(url)
    path = unquote(parts.path)
    for rule in rules:
        if parts.scheme not in rule['schemes']:
            continue
        if parts.netloc not in rule['netlocs']:
            continue
        for regex in rule['path_regexes']:
            m = re.search(regex, path)
            if m is None:
                continue
            result = callback(m)
            if result is not None:
                return result


# get_artifact_full_path {{{1
def get_artifact_path(task_id, path, work_dir=None):
    """Get the path to an artifact.

    Args:
        task_id (str): the ``taskId`` from ``upstreamArtifacts``
        path (str): the ``path`` from ``upstreamArtifacts``
        work_dir (str, optional): the *script ``work_dir``. If ``None``,
            return a relative path. Defaults to ``None``.

    Returns:
        str: the path to the artifact.

    """
    if work_dir is not None:
        base_dir = os.path.join(work_dir, 'cot')
    else:
        base_dir = 'cot'
    return os.path.join(base_dir, task_id, path)
