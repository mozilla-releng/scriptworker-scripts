#!/usr/bin/env python
"""Signing script
"""
import logging

log = logging.getLogger(__name__)


def main():
    config = {}
    if config['verbose']:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)
