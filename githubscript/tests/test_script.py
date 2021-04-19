import os
from contextlib import nullcontext as does_not_raise
from unittest.mock import MagicMock

import pytest

import githubscript.script as script


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, expectation",
    (
        ("release", does_not_raise()),
        ("non-existing", pytest.raises(NotImplementedError)),
    ),
)
async def test_async_main(monkeypatch, action, expectation):
    config = {"contact_github": "true", "github_projects": {"myproject": {}}}
    task = {"payload": {}}
    monkeypatch.setattr(script, "extract_common_scope_prefix", lambda *args: "some:prefix:")
    monkeypatch.setattr(script, "get_github_project", lambda *args: "myproject")
    monkeypatch.setattr(script, "get_release_config", lambda *args: {"release": "config"})
    monkeypatch.setattr(script, "get_action", lambda *args: action)
    monkeypatch.setattr(script, "check_action_is_allowed", lambda *args: None)

    async def _dummy_release(release_config):
        assert release_config == {"release": "config"}

    monkeypatch.setattr(script, "release", _dummy_release)
    with expectation:
        await script.async_main(config, task)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, expectation",
    (
        ("release", does_not_raise()),
        ("non-existing", pytest.raises(NotImplementedError)),
    ),
)
async def test_async_main_partialmatch(monkeypatch, action, expectation):
    config = {"contact_github": "true", "github_projects": {"myproj*": {}}}
    task = {"payload": {}}
    monkeypatch.setattr(script, "extract_common_scope_prefix", lambda *args: "some:prefix:")
    monkeypatch.setattr(script, "get_github_project", lambda *args: "myproject")
    monkeypatch.setattr(script, "get_release_config", lambda *args: {"release": "config"})
    monkeypatch.setattr(script, "get_action", lambda *args: action)
    monkeypatch.setattr(script, "check_action_is_allowed", lambda *args: None)

    async def _dummy_release(release_config):
        assert release_config == {"release": "config"}

    monkeypatch.setattr(script, "release", _dummy_release)
    with expectation:
        await script.async_main(config, task)


@pytest.mark.parametrize(
    "contact_github, expected_records, expected_text",
    (
        (False, 1, "This githubscript instance is not allowed to talk to Github."),
        (True, 0, None),
    ),
)
def test_warn_contact_github(caplog, monkeypatch, contact_github, expected_records, expected_text):
    script._warn_contact_github(contact_github)

    assert len(caplog.records) == expected_records
    if expected_records > 0:
        assert caplog.records[0].levelname == "WARNING"
        assert expected_text in caplog.text


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    assert script.get_default_config() == {
        "work_dir": os.path.join(parent_dir, "work_dir"),
        "verbose": False,
    }


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(script, "sync_main", sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())
