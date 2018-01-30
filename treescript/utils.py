"""Treescript general utility functions."""
# import asyncio
# from asyncio.subprocess import PIPE, STDOUT
# import functools
# import hashlib
import json
# import logging
# import os
# from shutil import copyfile
# import traceback
# from collections import namedtuple

# from signingscript.exceptions import FailedSubprocess, SigningServerError

# log = logging.getLogger(__name__)


def load_json(path):
    """Load json from path.

    Args:
        path (str): the path to read from

    Returns:
        dict: the loaded json object

    """
    with open(path, "r") as fh:
        return json.load(fh)
