import asyncio
import json
import logging
import os

from signingscript.exceptions import DownloadError

log = logging.getLogger(__name__)
# Mapping between signing client formats and file extensions
DETACHED_SIGNATURES = [
    ('gpg', '.asc', 'text/plain')
]


def mkdir(path):
    try:
        os.makedirs(path)
        log.info("mkdir {}".format(path))
    except OSError:
        pass


async def download_file(context, url, abs_filename, chunk_size=128):
    log.info("Downloading %s", url)
    parent_dir = os.path.dirname(abs_filename)
    async with context.session.get(url) as resp:
        if resp.status != 200:
            raise DownloadError("{} status {} is not 200!".format(url, resp.status))
        mkdir(parent_dir)
        with open(abs_filename, 'wb') as fd:
            while True:
                chunk = await resp.content.read(chunk_size)
                if not chunk:
                    break
                fd.write(chunk)
    log.info("Done")


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


async def log_output(fh):
    while True:
        line = await fh.readline()
        if line:
            log.info(line.decode("utf-8").rstrip())
        else:
            break


async def raise_future_exceptions(tasks):
    await asyncio.wait(tasks)
    for task in tasks:
        exc = task.exception()
        if exc is not None:
            raise exc
