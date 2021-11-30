import os

import pytest

from pushmsixscript.manifest import verify_msix

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def test_verify_msix_no_exist():
    with pytest.raises(FileNotFoundError):
        verify_msix("this.file.does.not.exist")


def test_verify_msix_invalid():
    with pytest.raises(KeyError):
        verify_msix(os.path.join(TEST_DATA_DIR, "valid-zip-invalid-content.msix"))


def test_verify_msix_valid():
    assert verify_msix(os.path.join(TEST_DATA_DIR, "valid-zip-valid-content.msix"))
