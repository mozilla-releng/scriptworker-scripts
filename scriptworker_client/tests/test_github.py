import pytest

from scriptworker_client import github


@pytest.mark.parametrize(
    "url, expected",
    (
        ("https://github.com/", True),
        ("https://github.com/some-user", True),
        ("https://github.com/some-user/some-repo", True),
        (
            "https://github.com/some-user/some-repo/raw/somerevision/.taskcluster.yml",
            True,
        ),
        ("https://hg.mozilla.org", False),
        (None, False),
        ("ssh://hg.mozilla.org/some-repo", False),
        ("ssh://github.com/some-user", True),
        ("ssh://github.com/some-user/some-repo.git", True),
    ),
)
def test_is_github_url(url, expected):
    assert github.is_github_url(url) == expected


@pytest.mark.parametrize(
    "repo_url, expected_user, expected_repo_name, raises",
    (
        (
            "https://github.com/mozilla-mobile/reference-browser",
            "mozilla-mobile",
            "reference-browser",
            False,
        ),
        (
            "https://github.com/mozilla-mobile/reference-browser.git",
            "mozilla-mobile",
            "reference-browser",
            False,
        ),
        (
            "https://github.com/mozilla-releng/staging-reference-browser",
            "mozilla-releng",
            "staging-reference-browser",
            False,
        ),
        (
            "https://github.com/mozilla-releng/staging-reference-browser/raw/0123456789abcdef0123456789abcdef01234567/.taskcluster.yml",
            "mozilla-releng",
            "staging-reference-browser",
            False,
        ),
        ("https://hg.mozilla.org/mozilla-central", None, None, True),
    ),
)
def test_extract_github_repo_owner_and_name(repo_url, expected_user, expected_repo_name, raises):
    if raises:
        with pytest.raises(ValueError):
            github.extract_github_repo_owner_and_name(repo_url)
    else:
        assert github.extract_github_repo_owner_and_name(repo_url) == (
            expected_user,
            expected_repo_name,
        )


@pytest.mark.parametrize(
    "repo_url, expected, raises",
    (
        (
            "https://github.com/mozilla-mobile/reference-browser",
            "mozilla-mobile/reference-browser",
            False,
        ),
        (
            "https://github.com/mozilla-mobile/reference-browser.git",
            "mozilla-mobile/reference-browser",
            False,
        ),
        (
            "https://github.com/mozilla-releng/staging-reference-browser",
            "mozilla-releng/staging-reference-browser",
            False,
        ),
        (
            "https://github.com/mozilla-releng/staging-reference-browser/raw/0123456789abcdef0123456789abcdef01234567/.taskcluster.yml",
            "mozilla-releng/staging-reference-browser",
            False,
        ),
        ("https://hg.mozilla.org/mozilla-central", None, True),
    ),
)
def test_extract_github_repo_full_name(repo_url, expected, raises):
    if raises:
        with pytest.raises(ValueError):
            github.extract_github_repo_full_name(repo_url)
    else:
        assert github.extract_github_repo_full_name(repo_url) == expected


@pytest.mark.parametrize(
    "repo_url, expected, raises",
    (
        (
            "https://github.com/mozilla-mobile/reference-browser",
            "git@github.com:mozilla-mobile/reference-browser.git",
            False,
        ),
        (
            "https://github.com/mozilla-mobile/reference-browser.git",
            "git@github.com:mozilla-mobile/reference-browser.git",
            False,
        ),
        (
            "https://github.com/mozilla-releng/staging-reference-browser",
            "git@github.com:mozilla-releng/staging-reference-browser.git",
            False,
        ),
        (
            "https://github.com/mozilla-releng/staging-reference-browser/raw/0123456789abcdef0123456789abcdef01234567/.taskcluster.yml",
            "git@github.com:mozilla-releng/staging-reference-browser.git",
            False,
        ),
        ("https://hg.mozilla.org/mozilla-central", None, True),
    ),
)
def test_extract_github_repo_ssh_url(repo_url, expected, raises):
    if raises:
        with pytest.raises(ValueError):
            github.extract_github_repo_ssh_url(repo_url)
    else:
        assert github.extract_github_repo_ssh_url(repo_url) == expected
