"""GitHub helper functions."""

from scriptworker_client.utils import get_parts_of_url_path


def is_github_url(url):
    """Tell if a given URL matches a Github one.

    Args:
        url (str): The URL to test. It can be None.
    Returns:
        bool: False if the URL is not a string or if it doesn't match a Github URL
    """
    if isinstance(url, str):
        return url.startswith(("https://github.com/", "ssh://github.com/"))
    else:
        return False


def extract_github_repo_owner_and_name(url):
    """Given an URL, return the repo name and who owns it.

    Args:
        url (str): The URL to the GitHub repository
    Raises:
        ValueError: on url that aren't from github
    Returns:
        str, str: the owner of the repository, the repository name
    """
    _check_github_url_is_supported(url)

    parts = get_parts_of_url_path(url)
    repo_owner = parts[0]
    repo_name = parts[1]

    return repo_owner, _strip_trailing_dot_git(repo_name)


def extract_github_repo_full_name(url):
    """Given an URL, return the full name of it.

    The full name is ``RepoOwner/RepoName``.
    Args:
        url (str): The URL to the GitHub repository
    Raises:
        ValueError: on url that aren't from github
    Returns:
        str: the full name.
    """
    return "/".join(extract_github_repo_owner_and_name(url))


def extract_github_repo_ssh_url(url):
    """Given an URL, return the ssh url.

    Args:
        url (str): The URL to the GitHub repository
    Raises:
        ValueError: on url that aren't from github
    Returns:
        str: the ssh url
    """
    return "git@github.com:{}.git".format(extract_github_repo_full_name(url))


def _strip_trailing_dot_git(url):
    if url.endswith(".git"):
        url = url[: -len(".git")]
    return url


def _check_github_url_is_supported(url):
    if not is_github_url(url):
        raise ValueError('"{}" is not a supported GitHub URL!'.format(url))
