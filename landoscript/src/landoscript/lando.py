import asyncio
import datetime
import logging
from pprint import pprint
from typing import Any, Callable, Tuple

from aiohttp import ClientResponseError, ClientSession
from async_timeout import timeout
from scriptworker.utils import calculate_sleep_time, retry_async

from landoscript.errors import LandoscriptError

log = logging.getLogger(__name__)


LandoAction = dict[str, str]


def create_commit_action(commitmsg: str, diff: str) -> LandoAction:
    """Return a `create-commit` lando action. Primarily exists to centralize the author name."""
    author = "Release Engineering Landoscript <release+landoscript@mozilla.com>"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {"action": "create-commit", "commitmsg": commitmsg, "diff": diff, "date": timestamp, "author": author}


async def submit(
    session: ClientSession,
    lando_api: str,
    lando_token: str,
    lando_repo: str,
    actions: list[LandoAction],
    sleeptime_callback: Callable[..., Any] = calculate_sleep_time,
) -> str:
    """Submit the provided `actions` to the given `lando_repo` through the `lando_api`."""
    url = f"{lando_api}/api/repo/{lando_repo}"
    json = {"actions": actions}

    log.info(f"submitting actions to lando: {actions}")
    async with timeout(30):
        log.info(f"submitting POST request to {url}")
        log.info("message body is:")
        log.info(pprint(json))

        submit_resp = await retry_async(
            session.post,
            args=(url,),
            kwargs={
                "json": json,
                "raise_for_status": True,
                "headers": {
                    "Authorization": f"Bearer {lando_token}",
                    "User-Agent": "Lando-User/release+landoscript@mozilla.com",
                },
            },
            attempts=10,
            retry_exceptions=ClientResponseError,
            sleeptime_callback=sleeptime_callback,
        )

    log.info(f"success! got {submit_resp.status} response")

    status_url = (await submit_resp.json()).get("status_url")
    if not status_url:
        raise LandoscriptError("couldn't find status url!")

    return status_url


async def poll_until_complete(session: ClientSession, poll_time: int, status_url: str):
    while True:
        log.info(f"sleeping {poll_time} seconds before polling for status")
        await asyncio.sleep(poll_time)

        log.info(f"polling lando for status: {status_url}")
        status_resp = await session.get(
            status_url,
            headers={"User-Agent": "Lando-User/release+landoscript@mozilla.com"},
        )

        # just retry if something went wrong...
        if not status_resp.ok:
            log.info(f"lando response is not ok (code {status_resp.status}), trying again...")
            continue

        if status_resp.status == 200:
            body = await status_resp.json()
            if body.get("status") != "LANDED":
                raise LandoscriptError("code is 200, status is not LANDED...result is unclear...failing!")

            log.info("success! got 200 response with 'LANDED' status")

            log.info("Commits are:")
            for commit in body["commits"]:
                log.info(commit)

            break


async def get_repo_info(session: ClientSession, lando_api: str, lando_repo: str) -> Tuple[str, str]:
    """Returns the URL and branch name for the given `lando_repo`, as provided
    by the `lando_api`."""
    url = f"{lando_api}/api/repoinfo/{lando_repo}"

    log.info(f"looking up repo info for {lando_repo}")
    async with timeout(30):
        resp = await retry_async(
            session.get,
            args=(url,),
            kwargs={
                "raise_for_status": True,
                "headers": {
                    "User-Agent": "Lando-User/release+landoscript@mozilla.com",
                },
            },
        )

        repo_info = await resp.json()
        log.info(f"found repo info: {repo_info}")

        return (repo_info["repo_url"], repo_info["branch_name"])
