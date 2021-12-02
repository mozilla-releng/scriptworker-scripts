#!/usr/bin/env python
# coding=utf-8
"""Test base files
"""


def touch(path):
    """Create an empty file.  Different from the system 'touch' in that it
    will overwrite an existing file.
    """
    with open(path, "w") as fh:
        print(path, file=fh, end="")
