import logging
from asyncio import ensure_future

import github3
from aiohttp_retry import RetryClient
from scriptworker_client.exceptions import TaskError
from scriptworker_client.utils import async_wrap, get_single_item_from_sequence, raise_future_exceptions, retry_async_decorator

log = logging.getLogger(__name__)


async def release(release_config):
    if not release_config["contact_github"]:
        log.warning('"contact_github" is set to False. No request to Github will be made')
        return

    # The token isn't needed anymore past this point. Let's take it out in order to avoid leaking
    # it in some debug logs.
    github_client = await _init_github_client(release_config.pop("github_token"))
    github_repository = await _get_github_repository(github_client, release_config)
    release_name = release_config["release_name"]
    git_tag = release_config["git_tag"]

    try:
        existing_release = await _get_release_from_tag(github_repository, git_tag)
        log.info(f"Release {release_name} already exists. Making sure it has the latest data...")
        await _update_release_if_needed(existing_release, release_config)
    except github3.exceptions.NotFoundError:
        log.info(f"Release {release_name} does not exist. Creating it...")
        await _create_release(github_repository, release_config)

    log.info("Making sure the latest artifacts are present...")
    existing_release = await _get_release_from_tag(github_repository, git_tag)
    await _upload_artifacts_if_needed(existing_release, release_config)

    log.info("All artifacts have been uploaded. Making sure everything went fine...")
    existing_release = await _get_release_from_tag(github_repository, git_tag)
    await _check_final_state_of_release(existing_release, release_config)
    log.info("Everything is sane!")


# The github3 library already retries requests. It gives a round of waiting of usually 15 seconds.
# A delay factor of 7.5s means the second round of waiting will occur ~15s after the first one,
# the third one ~30s and so on.
_GITHUB_LIBRARY_SLEEP_TIME_KWARGS = {"delay_factor": 7.5}
github_retry = retry_async_decorator(retry_exceptions=github3.exceptions.ServerError, sleeptime_kwargs=_GITHUB_LIBRARY_SLEEP_TIME_KWARGS)


@github_retry
async def _init_github_client(token):
    async_github_constructor = async_wrap(github3.GitHub)
    return await async_github_constructor(token=token)


@github_retry
async def _get_github_repository(github_client, release_config):
    async_get_github_repository = async_wrap(github_client.repository)
    return await async_get_github_repository(release_config["github_owner"], release_config["github_repo_name"])


@github_retry
async def _get_release_from_tag(github_repository, git_tag):
    async_release_from_tag = async_wrap(github_repository.release_from_tag)
    return await async_release_from_tag(git_tag)


@github_retry
async def _create_release(github_repository, release_config):
    async_create_release = async_wrap(github_repository.create_release)
    await async_create_release(**_get_github_release_kwargs(release_config))


@github_retry
async def _edit_existing_release(existing_release, release_config):
    async_edit_release = async_wrap(existing_release.edit)
    await async_edit_release(**_get_github_release_kwargs(release_config))


@github_retry
async def _delete_artifact(existing_artifact):
    async_delete_release = async_wrap(existing_artifact.delete)
    await async_delete_release()


@github_retry
async def _upload_artifact(existing_release, artifact):
    async_func = async_wrap(existing_release.upload_asset)

    with open(artifact["local_path"], "rb") as f:
        log.debug(f'Uploading artifact "{artifact["name"]}"...')
        await async_func(content_type=artifact["content_type"], name=artifact["name"], asset=f)


def _get_github_release_kwargs(release_config):
    return dict(
        tag_name=release_config["git_tag"],
        target_commitish=release_config["git_revision"],
        name=release_config["release_name"],
        draft=False,
        prerelease=release_config["is_prerelease"],
    )


async def _update_release_if_needed(existing_release, release_config):
    if not _does_release_need_to_be_updated(existing_release, release_config):
        log.info("Existing release already has the right data. Nothing to do.")
        return

    log.info("Existing release will be updated.")
    await _edit_existing_release(existing_release, release_config)


def _does_release_need_to_be_updated(existing_release, release_config):
    should_release_be_updated = False
    for config_field, github_field in (
        ("git_tag", "tag_name"),
        ("git_revision", "target_commitish"),
        ("release_name", "name"),
        ("is_prerelease", "prerelease"),
    ):
        target_value = release_config[config_field]
        existing_value = getattr(existing_release, github_field, None)
        if target_value != existing_value:
            log.info(f'Field "{config_field}" differ. Expected: {target_value}. Got: {existing_value}')
            should_release_be_updated = True

    return should_release_be_updated


async def _upload_artifacts_if_needed(existing_release, release_config):
    existing_artifacts = list(existing_release.assets())
    log.debug(f"Existing release has the following artifacts attached: {existing_artifacts}")

    coroutines = [ensure_future(_upload_artifact_if_needed(existing_release, existing_artifacts, artifact)) for artifact in release_config["artifacts"]]
    await raise_future_exceptions(coroutines)


async def _upload_artifact_if_needed(existing_release, existing_artifacts, artifact):
    artifact_name = artifact["name"]
    try:
        existing_artifact = _get_existing_artifact(existing_artifacts, artifact)
        if await _does_existing_artifact_need_to_be_reuploaded(existing_artifact, artifact):
            # XXX Updating releases only changes the metadata
            # https://developer.github.com/v3/repos/releases/#update-a-release-asset
            log.info(f'Artifact "{artifact_name}" exists but needs to be deleted and reuploaded. Doing so...')
            await _delete_artifact(existing_artifact)
        else:
            log.info(f'Artifact "{artifact_name}" has already been correctly uploaded to this Github release. Nothing to do.')
            return
    except ValueError:
        log.info(f'Artifact "{artifact_name}" does not exist on Github. Uploading...')

    await _upload_artifact(existing_release, artifact)


def _get_existing_artifact(existing_artifacts, target_artifact):
    return get_single_item_from_sequence(sequence=existing_artifacts, condition=lambda github_asset: github_asset.name == target_artifact["name"])


async def _does_existing_artifact_need_to_be_reuploaded(existing_artifact, target_artifact, retry_on_404=False):
    should_artifact_be_reuploaded = False

    artifact_name = target_artifact["name"]

    for field in ("size", "content_type"):
        target_value = target_artifact[field]
        existing_value = getattr(existing_artifact, field, None)
        if existing_value != target_value:
            log.info(f'Artifact "{artifact_name}" has its "{field}" differing. Expected: {target_value}. Got: {existing_value}')
            should_artifact_be_reuploaded = True

    # XXX For an unknown reason, Github sometimes fails to upload assets correctly. In this case:
    # the API does tell the artifact exists and has the expected size + content-type, but nothing
    # is displayed on the Web UI. Trying to download the URL exposed on the Web UI enables us to
    # catch this very issue.
    download_url = existing_artifact.browser_download_url
    # XXX A given release may be temporarilly 404 when it just got created
    retry_for_statuses = {404} if retry_on_404 else {}
    async with RetryClient() as client:
        # XXX We cannot do simple HEAD requests because Github uses AWS and they forbid them.
        # https://github.com/cavaliercoder/grab/issues/43#issuecomment-431076499
        async with client.get(download_url, retry_for_statuses=retry_for_statuses) as response:
            response_status = response.status
            if response_status != 200:
                log.warning(
                    f'Got an unexpected HTTP code when trying to download the existing artifact "{artifact_name}". Expected: 200. Got: {response_status}'
                )
                should_artifact_be_reuploaded = True

    return should_artifact_be_reuploaded


async def _check_final_state_of_release(existing_release, release_config):
    if _does_release_need_to_be_updated(existing_release, release_config):
        raise TaskError("Release still needs to be updated!")

    existing_artifacts = list(existing_release.assets())
    for artifact in release_config["artifacts"]:
        existing_artifact = _get_existing_artifact(existing_artifacts, artifact)
        if await _does_existing_artifact_need_to_be_reuploaded(existing_artifact, artifact, retry_on_404=True):
            raise TaskError(f'Artifact "{artifact["name"]}" needs to be reuploaded')
