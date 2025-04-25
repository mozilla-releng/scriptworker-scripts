import logging
from typing import Any, Callable

from aiohttp import ClientResponseError, ClientSession
from async_timeout import timeout
from scriptworker.utils import calculate_sleep_time, retry_async

log = logging.getLogger(__name__)


async def is_tree_open(session: ClientSession, treestatus_url: str, lando_repo: str, sleeptime_callback: Callable[..., Any] | None) -> bool:
    """Return True if we can land based on treestatus.

    Args:
        config (dict): the running config
        task (dict): the running task

    Returns:
        bool: ``True`` if the tree is open.

    """
    url = f"{treestatus_url}/trees/{lando_repo}"
    async with timeout(30):
        log.info(f"checking treestatus for {lando_repo}")
        resp = await retry_async(
            session.get,
            args=(url,),
            kwargs={"raise_for_status": True},
            attempts=10,
            retry_exceptions=ClientResponseError,
            sleeptime_callback=sleeptime_callback or calculate_sleep_time,
        )

    log.info(f"success! got {resp.status} response")
    treestatus = await resp.json()
    if treestatus["result"]["status"] != "closed":
        log.info("treestatus is %s - assuming we can land", repr(treestatus["result"]["status"]))
        return True

    return False
