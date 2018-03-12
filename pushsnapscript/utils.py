import contextlib
import os


@contextlib.contextmanager
def cwd(new_cwd):
    current_dir = os.getcwd()
    try:
        os.chdir(new_cwd)
        yield
    finally:
        os.chdir(current_dir)
