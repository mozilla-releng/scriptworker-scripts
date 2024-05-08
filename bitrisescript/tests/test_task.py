import inspect
from contextlib import nullcontext as does_not_raise

import pytest

import bitrisescript.task as task_mod
from scriptworker_client.exceptions import TaskVerificationError


@pytest.mark.parametrize(
    "config, task, expectation, expected_result",
    (
        (
            {"taskcluster_scope_prefixes": ["some:prefix"]},
            {"scopes": ["some:prefix:project:someproject"]},
            does_not_raise(),
            "some:prefix:",
        ),
        (
            {"taskcluster_scope_prefixes": ["some:prefix:"]},
            {"scopes": ["some:prefix:project:someproject"]},
            does_not_raise(),
            "some:prefix:",
        ),
        (
            {"taskcluster_scope_prefixes": ["some:prefix"]},
            {"scopes": ["some:prefix:project:someproject", "some:prefix:action:someaction"]},
            does_not_raise(),
            "some:prefix:",
        ),
        (
            {"taskcluster_scope_prefixes": ["another:prefix"]},
            {"scopes": ["some:prefix:project:someproject", "some:prefix:action:someaction"]},
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            {"taskcluster_scope_prefixes": ["some:prefix", "another:prefix"]},
            {"scopes": ["some:prefix:project:someproject", "another:prefix:action:someaction"]},
            pytest.raises(TaskVerificationError),
            None,
        ),
    ),
)
def test_extract_common_scope_prefix(config, task, expectation, expected_result):
    with expectation:
        assert task_mod.extract_common_scope_prefix(config, task) == expected_result


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
    "task, expectation, expected",
    (
        (
            {"scopes": ["test:prefix:app:foo", "test:prefix:workflow:bar", "test:prefix:workflow:baz"]},
            does_not_raise(),
            ["bar", "baz"],
        ),
        (
            {"scopes": ["test:prefix:app:foo"]},
            pytest.raises(TaskVerificationError),
            None,
        ),
    ),
)
def test_get_bitrise_workflows(config, task, expectation, expected):
    with expectation:
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


@pytest.mark.parametrize(
    "task, expectation, expected",
    (
        pytest.param({"payload": {}}, does_not_raise(), "work/artifacts", id="no artifact prefix"),
        pytest.param({"payload": {"artifact_prefix": "public"}}, does_not_raise(), "work/artifacts/public", id="artifact prefix"),
        pytest.param({"payload": {"artifact_prefix": "../../../etc"}}, pytest.raises(TaskVerificationError), None, id="funny business"),
    ),
)
def test_get_artifact_dir(config, task, expectation, expected):
    with expectation:
        assert task_mod.get_artifact_dir(config, task) == expected
