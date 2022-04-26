import json
import logging
import re

import xmltodict
from aiohttp_retry import RetryClient
from github3.exceptions import NotFoundError
from mozilla_version.maven import MavenVersion

import githubscript.application_services as appservices
import githubscript.github as github

from .constants import MAVEN

log = logging.getLogger(__name__)


def validate_gv_channel(c):
    """Validate that c is release, production or beta"""
    if c not in ("release", "beta", "nightly"):
        raise Exception(f"Invalid GV channel {c}")
    return c


def match_gv_version(src):
    """Find the GeckoView version in the contents of the given Gecko.kt file."""
    if match := re.compile(r'version = "([^"]*)"', re.MULTILINE).search(src):
        return MavenVersion.parse(match[1])
    raise Exception("Could not match the version in Gecko.kt")


def match_gv_channel(src):
    """Find the GeckoView channel in the contents of the given Gecko.kt file."""
    if match := re.compile(r"val channel = GeckoChannel.(NIGHTLY|BETA|RELEASE)", re.MULTILINE).search(src):
        return validate_gv_channel(match[1].lower())
    raise Exception("Could not match the channel in Gecko.kt")


async def get_latest_gv_version(gv_major_version, channel):
    """Find the last geckoview beta release version on Maven for the given major version"""
    channel = validate_gv_channel(channel)

    # Find the latest release in the multi-arch .aar
    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    # A-C builds against geckoview-omni
    # See https://github.com/mozilla-mobile/android-components/commit/0b349f48c91a50bb7b4ffbf40c6c122ed18142d3
    name += "-omni"

    async with RetryClient(raise_for_status=True) as client:
        async with client.get(f"{MAVEN}/org/mozilla/geckoview/{name}/maven-metadata.xml") as response:
            metadata = xmltodict.parse(await response.text())

    versions = []
    for version in metadata["metadata"]["versioning"]["versions"]["version"]:
        version = MavenVersion.parse(version)
        if version.major_number == gv_major_version:
            versions.append(version)

    if len(versions) == 0:
        raise Exception(f"Could not find any GeckoView {channel.capitalize()} {gv_major_version} releases")

    latest = max(versions)

    # Make sure this release has been uploaded for all architectures.

    for arch in ("arm64-v8a", "armeabi-v7a", "x86", "x86_64"):
        async with RetryClient(raise_for_status=True) as client:
            async with client.get(f"{MAVEN}/org/mozilla/geckoview/{name}-{arch}/{latest}/{name}-{arch}-{latest}.pom"):
                pass

    return latest


async def get_current_gv_channel_and_version(repo, branch_name):
    """Return the current gv channel used on the given release branch"""
    content_file = await github._get_contents(repo, "buildSrc/src/main/java/Gecko.kt", ref=branch_name)
    channel = match_gv_channel(content_file.decoded.decode("utf8"))
    version = match_gv_version(content_file.decoded.decode("utf8"))
    return channel, version


async def get_latest_glean_version(gv_version, channel):
    name = "geckoview"
    if channel != "release":
        name += "-" + channel
    # A-C builds against geckoview-omni
    # See https://github.com/mozilla-mobile/android-components/commit/0b349f48c91a50bb7b4ffbf40c6c122ed18142d3
    name += "-omni"

    async with RetryClient(raise_for_status=True) as client:
        async with client.get(f"{MAVEN}/org/mozilla/geckoview/{name}/{gv_version}/{name}-{gv_version}.module") as response:
            module_data = json.loads(await response.text())

    caps = module_data["variants"][0]["capabilities"]
    versions = [c["version"] for c in caps if c["group"] == "org.mozilla.telemetry" and c["name"] == "glean-native"]

    if len(versions) != 1:
        raise Exception(f"Could not find unique glean-native capability for GeckoView {channel.capitalize()} {gv_version}")

    return MavenVersion.parse(versions[0])


def match_glean_version(src):
    """Find the Glean version in the contents of the given Dependencies.kt file."""
    if match := re.compile(r'const val mozilla_glean = "([^"]*)"', re.MULTILINE).search(src):
        return MavenVersion.parse(match[1])
    raise Exception("Could not match glean in Dependencies.kt")


async def get_current_glean_version(ac_repo, branch_name):
    """Return the current Glean version used on the given release branch"""
    content_file = await github._get_contents(ac_repo, "buildSrc/src/main/java/Dependencies.kt", ref=branch_name)
    return match_glean_version(content_file.decoded.decode("utf8"))


async def _update_glean_version(ac_repo, old_glean_version, new_glean_version, branch, author):
    contents = await github._get_contents(ac_repo, "buildSrc/src/main/java/Dependencies.kt", ref=branch)
    content = contents.decoded.decode("utf-8")
    new_content = content.replace(
        f'mozilla_glean = "{old_glean_version}"',
        f'mozilla_glean = "{new_glean_version}"',
    )
    if content == new_content:
        raise Exception("Update to Dependencies.kt resulted in no changes: maybe the file was already up to date?")

    contents.update(
        f"Update Glean to {new_glean_version}.",
        new_content.encode("utf-8"),
        branch=branch,
        author=author,
    )


async def bump_geckoview(bump_config):
    """Bump Application-Services and GeckoView version in Android-Components"""
    if not bump_config["contact_github"]:
        log.warning('"contact_github" is set to False. No request to Github will be made')
        return

    github_client = await github._init_github_client(bump_config.pop("github_token"))
    ac_repo = await github._get_github_repository(github_client, bump_config)
    for release_branch_name in github.get_relevant_ac_branches(ac_repo):
        if release_branch_name == "main":
            await appservices.update_application_services(ac_repo, release_branch_name)
        await _update_geckoview(ac_repo, release_branch_name)


async def _update_geckoview(ac_repo, release_branch_name):
    gv_channel, gv_version = await get_current_gv_channel_and_version(ac_repo, release_branch_name)
    current_gv_major_version = gv_version.major_number
    latest_gv_version = await get_latest_gv_version(current_gv_major_version, gv_channel)
    current_glean_version = await get_current_glean_version(ac_repo, release_branch_name)
    latest_glean_version = await get_latest_glean_version(latest_gv_version, gv_channel)

    if gv_version >= latest_gv_version:
        log.info(f"No newer GV {gv_channel.capitalize()} release found. Exiting.")
        return

    log.info(f"We should update A-C {release_branch_name} with GV {gv_channel.capitalize()} {latest_gv_version}")

    pr_branch_name = f"releng/upgrade-geckoview-{current_gv_major_version}"
    try:
        pr_branch = await github._get_branch(ac_repo, pr_branch_name)
    except NotFoundError:
        pass
    else:
        if pr_branch:
            log.warning(f"The PR branch {pr_branch_name} already exists. Exiting.")
            return

    release_branch = await github._get_branch(ac_repo, release_branch_name)
    log.info(f"Last commit on {release_branch_name} is {release_branch.commit.sha}")

    ac_repo.create_branch_ref(pr_branch_name, sha=release_branch.commit.sha)
    await _update_gv_version(ac_repo, gv_version, latest_gv_version, pr_branch_name, gv_channel, None)
    if current_glean_version != latest_glean_version:
        await _update_glean_version(ac_repo, current_glean_version, latest_glean_version, pr_branch_name, None)

    # If we are updating a release branch then also update version.txt to
    # increment the patch version.
    # XXX we can remove this once A-C moves to shipit and version.txt is bumped post release
    if release_branch_name != "main":
        current_ac_version = await get_current_version(ac_repo, release_branch_name)
        next_ac_version = get_next_version(current_ac_version)
        log.info(f"Create an A-C {next_ac_version} release with GV {gv_channel.capitalize()} {latest_gv_version}")
        await _update_ac_version(ac_repo, current_ac_version, next_ac_version, pr_branch_name, None)
        # TODO Also update buildconfig until we do not need it anymore
        log.info("Updating buildconfig.yml")
        await _update_ac_buildconfig(ac_repo, current_ac_version, next_ac_version, pr_branch_name, None)

    # Create the pull request
    pr = ac_repo.create_pull(
        title=f"Update to GeckoView {gv_channel.capitalize()} {latest_gv_version} on {release_branch_name}",
        body=f"This (automated) patch updates GV {gv_channel.capitalize()} on main to {latest_gv_version}.",
        head=pr_branch_name,
        base=release_branch_name,
    )
    log.info(f"Pull request at {pr.html_url}")


async def _update_gv_version(ac_repo, old_gv_version, new_gv_version, branch, channel, author):
    contents = await github._get_contents(ac_repo, "buildSrc/src/main/java/Gecko.kt", ref=branch)
    content = contents.decoded.decode("utf-8")
    new_content = content.replace(
        f'const val version = "{old_gv_version}"',
        f'const val version = "{new_gv_version}"',
    )
    if content == new_content:
        raise Exception("Update to Gecko.kt resulted in no changes: maybe the file was already up to date?")

    contents.update(
        f"Update GeckoView ({channel.capitalize()}) to {new_gv_version}.",
        new_content.encode("utf-8"),
        branch=branch,
        author=author,
    )


async def get_current_version(repo, branch_name):
    content_file = await github._get_contents(repo, "version.txt", ref=branch_name)
    content = content_file.decoded.decode("utf8")
    return MavenVersion.parse(content.strip())


def get_next_version(version):
    return version.bump("patch_number")


async def _update_ac_version(ac_repo, current_version, next_version, branch, author):
    contents = await github._get_contents(ac_repo, "version.txt", ref=branch)
    content = contents.decoded.decode("utf-8")
    new_content = content.replace(current_version, next_version)
    if content == new_content:
        raise Exception("Update to version.txt resulted in no changes: maybe the file was already up to date?")

    contents.update(f"Set version to {next_version}.", new_content.encode("utf-8"), branch=branch, author=author)


async def _update_ac_buildconfig(ac_repo, current_version, next_version, branch, author):
    contents = await github._get_contents(ac_repo, ".buildconfig.yml", ref=branch)
    content = contents.decoded.decode("utf-8")
    new_content = re.sub(r"componentsVersion: \d+\.\d+\.\d+", f"componentsVersion: {next_version}", content)
    if content == new_content:
        log.warning("Update to .buildConfig.yml resulted in no changes: maybe the file was already up to date?")
        return

    contents.update(f"Set version to {next_version}.", new_content.encode("utf-8"), branch=branch, author=author)
