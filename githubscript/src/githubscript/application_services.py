import logging
import re

import requests
import xmltodict
from github3.exceptions import NotFoundError
from mozilla_version.maven import MavenVersion

from .constants import MAVEN
from .github import _get_branch, _get_contents

log = logging.getLogger(__name__)


def match_as_version(src):
    """Find the A-S version in the contents of the given Dependencies.kt file."""
    if match := re.compile(r'const val mozilla_appservices = "([^"]*)"', re.MULTILINE).search(src):
        return MavenVersion.parse(match[1])
    raise Exception("Could not match mozilla_appservices in Dependencies.kt")


async def get_current_as_version(ac_repo, release_branch_name):
    """Return the current as version used on the given release branch"""
    content_file = await _get_contents(ac_repo, "buildSrc/src/main/java/Dependencies.kt", ref=release_branch_name)
    return match_as_version(content_file.decoded.decode("utf8"))


def get_latest_as_version(as_major_version):
    """Find the last A-S version on Maven for the given major version"""

    # Find the latest release in the multi-arch .aar

    # TODO What is the right package to check here? full-megazord metadata seems broken.
    r = requests.get(f"{MAVEN}/org/mozilla/appservices/nimbus/maven-metadata.xml")
    r.raise_for_status()
    metadata = xmltodict.parse(r.text)

    versions = []
    for version in metadata["metadata"]["versioning"]["versions"]["version"]:
        version = MavenVersion.parse(version)
        if version.major_number == as_major_version:
            versions.append(version)

    if not versions:
        raise Exception(f"Could not find any A-S {as_major_version} releases")

    # Make sure this release has been uploaded for all architectures.

    # TODO Do we need to do this?

    # for arch in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
    #    r = requests.get(f"{MAVEN}/org/mozilla/geckoview/{name}-{arch}/{latest}/{name}-{arch}-{latest}.pom")
    #    r.raise_for_status()

    return max(versions)


async def _update_as_version(ac_repo, old_as_version, new_as_version, branch, author):
    contents = await _get_contents(ac_repo, "buildSrc/src/main/java/Dependencies.kt", ref=branch)
    content = contents.decoded.decode("utf-8")
    new_content = content.replace(
        f'mozilla_appservices = "{old_as_version}"',
        f'mozilla_appservices = "{new_as_version}"',
    )
    if content == new_content:
        raise Exception("Update to Dependencies.kt resulted in no changes: maybe the file was already up to date?")

    contents.update(
        f"Update A-S to {new_as_version}.",
        new_content.encode("utf-8"),
        branch=branch,
        author=author,
    )


async def update_application_services(ac_repo, release_branch_name):
    log.info(f"Updating A-S on {ac_repo.full_name}:{release_branch_name}")
    current_as_version = await get_current_as_version(ac_repo, release_branch_name)
    log.info(f"Current A-S version on A-C {release_branch_name} is {current_as_version}")
    latest_as_version = get_latest_as_version(current_as_version.major_number)
    log.info(f"Latest A-S version available is {latest_as_version}")
    if current_as_version >= latest_as_version:
        log.info("No newer A-S release found. Skipping.")
        return
    # Create a non unique PR branch name for work on this ac branch.
    pr_branch_name = f"releng/update-as/ac-{release_branch_name}"
    try:
        pr_branch = await _get_branch(ac_repo, pr_branch_name)
    except NotFoundError:
        pass
    else:
        if pr_branch:
            log.warning(f"The PR branch {pr_branch_name} already exists. Skipping.")
            return

    release_branch = await _get_branch(ac_repo, release_branch_name)
    log.info(f"Last commit on {release_branch_name} is {release_branch.commit.sha}")
    ac_repo.create_branch_ref(pr_branch_name, sha=release_branch.commit.sha)
    await _update_as_version(ac_repo, current_as_version, latest_as_version, pr_branch_name, None)
    pr = ac_repo.create_pull(
        title=f"Update to A-S {latest_as_version} on {release_branch_name}",
        body=f"This (automated) patch updates A-S to {latest_as_version}.",
        head=pr_branch_name,
        base=release_branch_name,
    )
    log.info(f"Pull request at {pr.html_url}")
