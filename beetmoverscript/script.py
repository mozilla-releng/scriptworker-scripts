#!/usr/bin/env python
"""Beetmover script
"""
import logging
import sys
log = logging.getLogger(__name__)



# async_main {{{1
def async_main(context):
    log.info("Hello Scriptworker!")


# main {{{1
def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(name=None, config_path=None):
    if name not in (None, '__main__'):
        return
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]

    log_level = logging.DEBUG
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)

    async_main(config_path)

main(name=__name__)
