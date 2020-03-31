import os

import pytest

from treescript.mercurial import HGRCPATH

ROBUSTCHECKOUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "vendored", "robustcheckout.py"))
HGRC_ROBUSTCHECKOUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "robustcheckout.hgrc"))


@pytest.fixture(autouse=True)
def set_hgrc(monkeypatch):
    monkeypatch.setenv("HGRCPATH", os.path.pathsep.join([HGRCPATH, HGRC_ROBUSTCHECKOUT]))
    monkeypatch.setenv("ROBUSTCHECKOUT", ROBUSTCHECKOUT_PATH)
