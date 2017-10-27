import requests
import requests_mock
import tempfile

from unittest.mock import MagicMock

from mozapkpublisher.common.utils import load_json_url, file_sha512sum, download_file


def test_load_json_url(monkeypatch):
    response_mock = MagicMock()
    response_mock.json = MagicMock()
    monkeypatch.setattr(requests, 'get', lambda url: response_mock)
    load_json_url('https://dummy-url.tld')
    response_mock.json.assert_called_once_with()


def test_download_file(monkeypatch):
    with requests_mock.Mocker() as m:
        origin_data = b'a' * 1025
        m.get('https://dummy-url.tld/file', content=origin_data)

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
