import logging

log = logging.getLogger(__name__)


def log_file_contents(contents: str):
    for line in contents.splitlines():
        log.info(line)
