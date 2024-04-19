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
    "task_payload, expected",
    (
        # Simple payload with no global_params
        (
            {},
            [{"workflow_id": "wkflw"}],
        ),
        # Simple payload with global_params
        (
            {"global_params": {"foo": "bar"}},
            [{"foo": "bar"}],
        ),
        # Payload with multiple workflow_params
        (
            {"global_params": {"foo": "bar"}, "workflow_params": {"wkflw": [{"baz": "qux"}, {"tap": "zab"}]}},
            [
                {"foo": "bar", "baz": "qux"},
                {"foo": "bar", "tap": "zab"},
            ],
        ),
        # Payload with workflow_params but no global_params
        (
            {"workflow_params": {"wkflw": [{"baz": "qux"}]}},
            [{"baz": "qux"}],
        ),
        # Payload with workflow_params and overriding workflow_params
        (
            {"global_params": {"foo": "bar"}, "workflow_params": {"wkflw": [{"baz": "qux"}, {"foo": "zab"}]}},
            [
                {"foo": "bar", "baz": "qux"},
                {"foo": "zab"},
            ],
        ),
        # Complex global_params and workflow_params
        (
            {
                "global_params": {"environment": {"var1": "value1"}},
                "workflow_params": {
                    "wkflw": [
                        {"environment": {"var2": "value2"}},
                        {"environment": {"var3": "value3"}},
                        # Override var1
                        {"environment": {"var3": "value3", "var1": "OVERRIDE"}},
                    ]
                },
            },
            [
                {"environment": {"var1": "value1", "var2": "value2"}},
                {"environment": {"var1": "value1", "var3": "value3"}},
                {"environment": {"var1": "OVERRIDE", "var3": "value3"}},
            ],
        ),
    ),
)
def test_get_build_params(task_payload, expected):
    # workflow_id should always be inserted into build_params
    assert task_mod.get_build_params({"payload": task_payload}, "wkflw") == [{"workflow_id": "wkflw", **item} for item in expected]


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
