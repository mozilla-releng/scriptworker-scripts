import os
import pytest
import sys

from contextlib import contextmanager
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.get_l10n_strings import main


@contextmanager
def working_directory(path):
    original_cwd = os.getcwd()
    os.chdir(str(path))
    yield
    os.chdir(original_cwd)


def test_main(tmp_path, monkeypatch):
    # get_l10n_strings produces a file in the working directory
    with working_directory(tmp_path):
        print('cwd is {}', os.getcwd())

        incomplete_args = [
            '--output-file', 'some_file',
        ]

        monkeypatch.setattr(sys, 'argv', incomplete_args)

        with pytest.raises(SystemExit):
            main()
