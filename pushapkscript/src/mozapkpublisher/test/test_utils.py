import itertools
import pytest
import requests
import sys
import tempfile

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from mozapkpublisher.utils import load_json_url, file_sha512sum, download_file


def test_load_json_url(monkeypatch):
    response_mock = MagicMock()
    response_mock.json = MagicMock()
    monkeypatch.setattr(requests, 'get', lambda url: response_mock)
    load_json_url('https://dummy-url.tld')
    response_mock.json.assert_called_once_with()


@pytest.mark.skipif(sys.version_info[0] == 3, reason='This mock does not work as expected in Python 3')
def test_download_file(monkeypatch):
    response_mock = MagicMock()
    origin_data = b'a' * 1025

    response_mock.iter_content = lambda chunk_size: itertools.chain(origin_data)
    monkeypatch.setattr(requests, 'get', lambda url, stream: response_mock)

    with tempfile.NamedTemporaryFile() as temp_file:
        download_file('https://dummy-url.tld/file', temp_file.name)
        temp_file.seek(0)
        data = temp_file.read()
    assert data == origin_data


def test_file_sha512sum():
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(b'known sha512')
        temp_file.seek(0)

        assert file_sha512sum(temp_file.name) == '0b1622c08ae1fcffe9f0d1dd17fe273d7e8c96668981c8a38f6bbfa4f757b30af0\
ed2aabf90f1f8a5983082a0b88194fe81bc850d3019fd9eca9328584227c84'
