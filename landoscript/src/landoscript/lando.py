import asyncio
import logging
from pprint import pprint

from aiohttp import ClientResponseError
from async_timeout import timeout
from scriptworker.utils import calculate_sleep_time, retry_async

from landoscript.errors import LandoscriptError

log = logging.getLogger(__name__)


async def submit(session, lando_api, lando_repo, actions, sleeptime_callback=calculate_sleep_time):
    url = f"{lando_api}/api/v1/{lando_repo}"
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


async def poll_until_complete(session, poll_time, status_url):
    while True:
        await asyncio.sleep(poll_time)

        log.info(f"polling lando for status: {status_url}")
        status_resp = await session.get(status_url)

        # just retry if something went wrong...
        if not status_resp.ok:
            log.info(f"lando response is not ok (code {status_resp.status}), trying again...")
            continue

        if status_resp.status == 200:
            body = await status_resp.json()
            if body.get("status") != "completed":
                raise LandoscriptError("code is 200, status is not completed...weird?")

            log.info("success! got 200 response")

            log.info("Commits are:")
            # TODO: verify the number of commits is the same as expected
            for commit in body["commits"]:
                log.info(commit)

            break
