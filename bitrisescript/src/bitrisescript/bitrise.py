import asyncio
import logging
import os
from pprint import pformat
from typing import Any

from aiohttp_retry import RetryClient

from bitrisescript.exceptions import BitriseBuildException
from scriptworker_client.exceptions import TaskVerificationError
from scriptworker_client.utils import get_single_item_from_sequence

BITRISE_API_URL = "https://api.bitrise.io/v0.1"

log = logging.getLogger(__name__)


class BitriseClient:
    """A singleton to facilite sharing client across requests."""

    _instance = None
    _client = None
    base: str = BITRISE_API_URL
    prefix: str = ""
    headers: dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._client = RetryClient()
        return cls._instance

    async def close(self):
        if self._client:
            await self._client.close()

    def set_auth(self, token: str):
        """Sets the Bitrise authorization header to the provided access token.

        Args:
            token (str): Bitrise API token.
        """
        self.headers["Authorization"] = token

    async def set_app_prefix(self, app: str):
        """Sets the client's prefix to the specified Bitrise app.

        This scopes the client to only the specified application.

        Args:
            app (str): Name of the Bitrise application to scope to.
        """
        apps = await self.request("/apps")
        app_slug = get_single_item_from_sequence(
            sequence=apps,
            condition=lambda obj: obj["repo_slug"] == app,
            ErrorClass=TaskVerificationError,
            no_item_error_message=f"No Bitrise app matching '{app}' found!",
            too_many_item_error_message=f"More than one Bitrise app matching '{app}' found!",
        )["slug"]
        self.prefix = f"/apps/{app_slug}"

    async def request(self, endpoint: str, method: str = "get", **kwargs: Any) -> Any:
        """Perform a request against the Bitrise API.

        Args:
            endpoint (str): The API endpoint to query, is appended to the current prefix.
            method (str): The HTTP method to use (default: get).
            kwargs (Any): Extra args to pass down to ``RetryClient.request``.

        Returns:
            dict: The JSON response of the request.
        """
        assert self._client

        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        endpoint = f"{self.prefix}{endpoint}"
        method_and_url = f"{method.upper()} {endpoint}"
        log.debug(f"Making request {method_and_url}...")

        url = f"{self.base}{endpoint}"
        kwargs.setdefault("headers", {}).update(self.headers)

        data = []
        while True:
            r = await self._client.request(method, url, **kwargs)
            log.debug(f"{method_and_url} returned HTTP code {r.status}")
            if r.status >= 400:
                log.debug(f"{method_and_url} returned JSON:\n{pformat(data)}")
                r.raise_for_status()

            response = await r.json()

            if "data" not in response:
                data = response
                break

            if isinstance(response["data"], dict):
                data = response["data"]
                break

            # Data is a list we need to handle possible pagination.
            data.extend(response["data"])
            next = response.get("paging", {}).get("next")
            if not next:
                break
            kwargs.setdefault("params", {})["next"] = next

        return data


async def wait_for_build_finish(build_slug: str, poll_interval: int = 60) -> None:
    """Waits for the given Bitrise build_slug to finish.

    Args:
        build_slug (str): The Bitrise build to wait on.
        poll_interval (int): Time in seconds to poll the build (default: 60).
    """
    client = BitriseClient()
    endpoint = f"/builds/{build_slug}"

    while True:
        data = await client.request(endpoint)

        if data["finished_at"]:
            log.info(f"Build {build_slug} is finished")
            break

        log.debug(f"Build {build_slug} is still running, waiting {poll_interval}s...")
        await asyncio.sleep(poll_interval)

    if data["status_text"] != "success":
        raise BitriseBuildException(build_slug, data)


async def download_artifacts(build_slug: str, artifacts_dir: str) -> None:
    """Download all artifacts from the given Bitrise build.

    Args:
        build_slug (str): The Bitrise build to download artifacts from.
        artifacts_dir (str): Directory to save artifacts to.
    """
    client = BitriseClient()
    endpoint = f"/builds/{build_slug}/artifacts"
    response = await client.request(endpoint)

    artifacts_metadata = {metadata["slug"]: metadata["title"] for metadata in response}

    for artifact_slug, title in artifacts_metadata.items():
        endpoint = f"/builds/{build_slug}/artifacts/{artifact_slug}"
        data = await client.request(endpoint)

        download_url = data["expiring_download_url"]
        await download_file(download_url, os.path.join(artifacts_dir, title))


async def download_log(build_slug: str, artifacts_dir: str, poll_interval: int = 60) -> None:
    """Download the log from the given Bitrise build.

    Args:
        build_slug (str): The Bitrise build to download the log from.
        artifacts_dir (str): Directory to save artifacts to.
        poll_interval (int): Time in seconds to poll for completion of log (default: 60).
    """
    client = BitriseClient()
    endpoint = f"/builds/{build_slug}/log"

    while True:
        response = await client.request(endpoint)
        if response["is_archived"] is True:
            log.info(f"Log for build '{build_slug}' is now ready")
            break
        else:
            log.info(f"Log for build '{build_slug}' is still running. Waiting another minute...")
            await asyncio.sleep(poll_interval)

    download_url = response["expiring_raw_log_url"]
    if download_url:
        await download_file(download_url, os.path.join(artifacts_dir, "bitrise.log"))
    else:
        log.error(f"Bitrise has no log for build '{build_slug}'. Please check https://app.bitrise.io/build/{build_slug}")


async def download_file(download_url: str, file_destination: str, chunk_size: int = 512) -> None:
    """Download a file.

    Args:
        download_url (str): Url to download.
        file_destination (str): Path to save the file.
        chunk_size (int): Size in bytes to stream to disk at a time (default: 512).
    """
    async with RetryClient() as client:
        async with client.get(download_url) as resp:
            with open(file_destination, "wb") as fd:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    fd.write(chunk)

    log.info(f"'{file_destination}' downloaded")


async def run_build(artifacts_dir: str, workflow_id: str, **build_params: Any) -> None:
    """Run the bitrise build corresponding to the specified worlfow and build params.

    Args:
        artifacts_dir (str): Directory to download artifacts to.
        workflow_id (str): Identifier of workflow to run.
        build_params (Any): Additional build_params to forward to bitrise.
    """
    client = BitriseClient()

    artifacts_dir = os.path.join(artifacts_dir, workflow_id)
    if not os.path.isdir(artifacts_dir):
        os.makedirs(artifacts_dir)

    build_params["workflow_id"] = workflow_id
    data = {
        "hook_info": {
            "type": "bitrise",
        },
        "build_params": build_params,
    }

    response = await client.request("/builds", method="post", json=data)
    if response.get("status", "") != "ok":
        raise Exception(f"Bitrise status for '{workflow_id}' is not ok. Got: {response}")

    build_slug = response["build_slug"]

    log.info(f"Created new job for '{workflow_id}'. Slug: {build_slug}")

    try:
        await wait_for_build_finish(build_slug)
        log.info(f"Build '{build_slug}' is successful. Retrieving artifacts...")
        await download_artifacts(build_slug, artifacts_dir)
    finally:
        log.info(f"Retrieving bitrise log for '{build_slug}'...")
        await download_log(build_slug, artifacts_dir)
