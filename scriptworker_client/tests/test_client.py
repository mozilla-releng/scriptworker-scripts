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


@pytest.mark.parametrize('data,schema,raises', ((
    {
        "list-of-strings": ['a', 'b'],
    },
    {
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
    },
    False
), (
    {
        "list-of-strings": ['a', 'a'],
    },
    {
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
    },
    True
), (
    {
        "list-of-strings": [],
    },
    {
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
    },
    True
), (
    {
        "list-of-strings": {"foo": "bar"},
    },
    {
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
    },
    True
), (
    {
        "invalid-key": {},
    },
    {
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
    },
    True
)))
def test_verify_json_schema(data, schema, raises):
    if raises:
        with pytest.raises(TaskVerificationError):
            client.verify_json_schema(data, schema)
    else:
        client.verify_json_schema(data, schema)
