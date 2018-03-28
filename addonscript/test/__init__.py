"""Common utilities for the test harness."""
# import os
import pytest
import tempfile


# def read_file(path):
#     with open(path, 'r') as fh:
#         return fh.read()


# BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
# PUB_KEY_PATH = os.path.join(TEST_DATA_DIR, "id_rsa.pub")


# def noop_sync(*args, **kwargs):
#     pass


# async def noop_async(*args, **kwargs):
#     pass


@pytest.yield_fixture(scope='function')
def tmpdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


# def is_slice_in_list(s, l):
#     # Credit to https://stackoverflow.com/a/20789412/#answer-20789669
#     # With edits by Callek to be py3 and pep8 compat
#     len_s = len(s)  # so we don't recompute length of s on every iteration
#     return any(s == l[i:len_s + i] for i in range(len(l) - len_s + 1))
