import inspect
from contextlib import nullcontext as does_not_raise

import pytest

import bitrisescript.task as task_mod
from scriptworker_client.exceptions import TaskVerificationError


@pytest.mark.parametrize(
    "task, expectation",
    (
        pytest.param({"scopes": ["test:prefix:app:foo", "test:prefix:workflow:bar"]}, does_not_raise(), id="valid"),
        pytest.param({"scopes": ["bad:prefix:app:foo", "test:prefix:workflow:bar"]}, pytest.raises(TaskVerificationError), id="invalid"),
        pytest.param({"scopes": ["test:prefix:app:foo", "bad:prefix:workflow:bar"]}, pytest.raises(TaskVerificationError), id="invalid"),
    ),
)
def test_validate_scope_prefixes(config, task, expectation):
    with expectation:
        task_mod.validate_scope_prefixes(config, task)


@pytest.mark.parametrize(
    "task, prefix, expectation, expected_result",
    (
        (
            "some:prefix:chunk",
            "some:prefix:",
            does_not_raise(),
            "chunk",
        ),
        (
            "some:bigger:prefix:chunk",
            "some:bigger:prefix:",
            does_not_raise(),
            "chunk",
        ),
        (
            "some:prefix:bigger:chunk",
            "some:prefix:",
            does_not_raise(),
            "bigger:chunk",
        ),
    ),
)
def test_extract_last_chunk_of_scope(task, prefix, expectation, expected_result):
    with expectation:
        assert task_mod._extract_last_chunk_of_scope(task, prefix) == expected_result


@pytest.mark.parametrize(
    "task, expected",
    (
        pytest.param({"scopes": ["test:prefix:app:foo"]}, "foo", id="valid"),
        pytest.param({"scopes": ["test:prefix:workflow:bar"]}, TaskVerificationError, id="missing"),
        pytest.param({"scopes": ["test:prefix:app:foo", "test:prefix:app:bar"]}, TaskVerificationError, id="multiple"),
    ),
)
def test_get_bitrise_app(config, task, expected):
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            task_mod.get_bitrise_app(config, task)
    else:
        assert task_mod.get_bitrise_app(config, task) == expected


@pytest.mark.parametrize(
    "task, expected",
    (
        (
            {"scopes": ["test:prefix:app:foo", "test:prefix:workflow:bar", "test:prefix:workflow:baz"]},
            ["bar", "baz"],
        ),
        (
            {"scopes": ["test:prefix:app:foo"]},
            [],
        ),
    ),
)
def test_get_bitrise_workflows(config, task, expected):
    assert task_mod.get_bitrise_workflows(config, task) == expected


@pytest.mark.parametrize(
    "task, expected",
    (
        (
            {"payload": {}},
            {},
        ),
        (
            {"payload": {"build_params": "foo"}},
            "foo",
        ),
    ),
)
def test_get_build_params(task, expected):
    assert task_mod.get_build_params(task) == expected
