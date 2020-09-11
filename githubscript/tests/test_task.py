from contextlib import nullcontext as does_not_raise

import pytest
from scriptworker_client.exceptions import TaskVerificationError

import githubscript.task as gstask


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
        assert gstask.extract_common_scope_prefix(config, task) == expected_result


@pytest.mark.parametrize(
    "config, expected_result",
    (
        (
            {"taskcluster_scope_prefixes": ["some:prefix:"]},
            ["some:prefix:"],
        ),
        (
            {"taskcluster_scope_prefixes": ["some:prefix:", "another:prefix"]},
            ["some:prefix:", "another:prefix:"],
        ),
        (
            {"taskcluster_scope_prefixes": []},
            [],
        ),
    ),
)
def test_get_allowed_scope_prefixes(config, expected_result):
    assert gstask._get_allowed_scope_prefixes(config) == expected_result


@pytest.mark.parametrize(
    "task, prefix, expectation, expected_result",
    (
        (
            {"scopes": ["some:prefix:action:someaction"]},
            "some:prefix:",
            does_not_raise(),
            "someaction",
        ),
        (
            {"scopes": []},
            "some:prefix:",
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            {"scopes": ["some:prefix:action:someaction", "some:prefix:action:anotheraction"]},
            "some:prefix:",
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            {"scopes": ["some:prefix:action:someaction"]},
            "some:prefix:action:",
            pytest.raises(TaskVerificationError),
            None,
        ),
    ),
)
def test_get_action(task, prefix, expectation, expected_result):
    with expectation:
        assert gstask.get_action(task, prefix) == expected_result


@pytest.mark.parametrize(
    "task, prefix, expectation, expected_result",
    (
        (
            {"scopes": ["some:prefix:project:someproject"]},
            "some:prefix:",
            does_not_raise(),
            "someproject",
        ),
        (
            {"scopes": []},
            "some:prefix:",
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            {"scopes": ["some:prefix:project:someproject", "some:prefix:project:anotherproject"]},
            "some:prefix:",
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            {"scopes": ["some:prefix:project:someproject"]},
            "some:prefix:project:",
            pytest.raises(TaskVerificationError),
            None,
        ),
    ),
)
def test_get_github_project(task, prefix, expectation, expected_result):
    with expectation:
        assert gstask.get_github_project(task, prefix) == expected_result


@pytest.mark.parametrize(
    "task, prefix, expectation, expected_result",
    (
        (
            {"scopes": ["some:prefix:chunk"]},
            "some:prefix:",
            does_not_raise(),
            "chunk",
        ),
        (
            {"scopes": ["some:bigger:prefix:chunk"]},
            "some:bigger:prefix:",
            does_not_raise(),
            "chunk",
        ),
        (
            {"scopes": ["some:prefix:bigger:chunk"]},
            "some:prefix:",
            does_not_raise(),
            "bigger:chunk",
        ),
        (
            {"scopes": []},
            "some:prefix:",
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            {"scopes": ["some:prefix:chunk", "some:prefix:anotherchunk"]},
            "some:prefix:",
            pytest.raises(TaskVerificationError),
            None,
        ),
    ),
)
def test_extract_last_chunk_of_scope(task, prefix, expectation, expected_result):
    with expectation:
        assert gstask._extract_last_chunk_of_scope(task, prefix) == expected_result


@pytest.mark.parametrize(
    "project_config, action, expectation",
    (
        (
            {"allowed_actions": ["someaction"]},
            "someaction",
            does_not_raise(),
        ),
        (
            {"allowed_actions": []},
            "someaction",
            pytest.raises(TaskVerificationError),
        ),
        (
            {"allowed_actions": ["anotheraction"]},
            "someaction",
            pytest.raises(TaskVerificationError),
        ),
    ),
)
def test_check_action_is_allowed(project_config, action, expectation):
    with expectation:
        gstask.check_action_is_allowed(project_config, action)
