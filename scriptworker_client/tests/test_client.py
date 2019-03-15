#!/usr/bin/env python
# coding=utf-8
"""Test scriptworker_client.client
"""
import json
import os
import pytest
import tempfile
import scriptworker_client.client as client
from scriptworker_client.exceptions import TaskVerificationError


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
    if raises:
        with pytest.raises(TaskVerificationError):
            client.verify_json_schema(data, schema)
    else:
        client.verify_json_schema(data, schema)


# verify_task_schema {{{1
def test_verify_task_schema():
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
