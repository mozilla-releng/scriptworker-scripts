import os
import tempfile

from pushsnapscript.utils import cwd


def test_cwd():
    old_working_dir = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        with cwd(d):
            current_working_dir = os.getcwd()
            assert current_working_dir == d
            assert old_working_dir != current_working_dir

        assert old_working_dir == os.getcwd()
