import sys

import pytest

import build_decision.cli as cli
import build_decision.cron as cron
import build_decision.hg_push as hg_push


def test_hg_push(mocker):
    """Add hg-push cli coverage."""
    options = {
        "dry_run": True,
        "repository": "fakerepo",
        "repo_url": "fakeurl",
        "project": "fakeproject",
        "level": "fakelevel",
        "repository_type": "fake_repository_type",
        "trust_domain": "fake_trust_domain",
    }

    fake_repo = mocker.MagicMock()

    def fake_build_decision(repository, dry_run):
        assert repository is fake_repo
        assert dry_run

    mocker.patch.object(hg_push, "build_decision", new=fake_build_decision)
    mocker.patch.object(cli, "Repository", return_value=fake_repo)
    cli.hg_push(options)


@pytest.mark.parametrize(
    "token, force_run",
    (
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ),
)
def test_cron(mocker, token, force_run):
    """Add cron cli coverage.

    Parametrize ``token`` for ``repo_arguments`` coverage.
    """
    options = {
        "dry_run": True,
        "repository": "fakerepo",
        "repo_url": "fakeurl",
        "project": "fakeproject",
        "level": "fakelevel",
        "repository_type": "fake_repository_type",
        "trust_domain": "fake_trust_domain",
        "branch": "branch",
        "force_run": force_run,
    }
    if token:
        options["github_token_secret"] = "token_secret"

    fake_repo = mocker.MagicMock()

    def fake_run(repository, branch, force_run, dry_run):
        assert repository is fake_repo
        assert branch == "branch"
        assert force_run == options["force_run"]
        assert dry_run

    mocker.patch.object(cli, "get_secret")
    mocker.patch.object(cron, "run", new=fake_run)
    mocker.patch.object(cli, "Repository", return_value=fake_repo)
    cli.cron(options)


def test_main_help(mocker):
    """Call cli.main() with --help."""
    mocker.patch.object(sys, "argv", new=["--help"])
    with pytest.raises(SystemExit):
        cli.main()
