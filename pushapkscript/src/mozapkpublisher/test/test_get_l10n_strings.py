import pytest
import sys

from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.get_l10n_strings import main


def test_main(monkeypatch):
    incomplete_args = [
        '--output-file', 'some_file',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(WrongArgumentGiven):
        main()
