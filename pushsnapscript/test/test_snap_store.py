import pytest
import tempfile

from unittest.mock import MagicMock

from pushsnapscript.snap_store import snapcraft_store_client, push, _session


@pytest.mark.parametrize('channel', ('beta', 'candidate'))
def test_push(monkeypatch, channel):
    push_call_count = (n for n in range(0, 2))
    login_call_count = (n for n in range(0, 3))

    context = MagicMock()
    store_client_mock = MagicMock()
    monkeypatch.setattr('snapcraft.storeapi.StoreClient', lambda: store_client_mock)

    with tempfile.NamedTemporaryFile('w+') as fake_macaroon:
        context.config = {
            'macaroons_locations': {channel: fake_macaroon.name}
        }

        def snapcraft_store_client_login_fake(store, config_fd):
            assert store == store_client_mock
            assert config_fd.name == fake_macaroon.name
            next(login_call_count)

        def snapcraft_store_client_push_fake(snap_filename, release_channels):
            assert snap_filename == '/some/file.snap'
            assert release_channels == [channel]
            next(push_call_count)

        monkeypatch.setattr(snapcraft_store_client, 'login', snapcraft_store_client_login_fake)
        monkeypatch.setattr(snapcraft_store_client, 'push', snapcraft_store_client_push_fake)
        push(context, '/some/file.snap', channel)

    assert next(push_call_count) == 1
    assert next(login_call_count) == 1
    store_client_mock.logout.assert_called_once_with()


def test_push_early_return_if_not_allowed(monkeypatch):
    call_count = (n for n in range(0, 2))

    context = MagicMock()

    def increase_call_count(_, __):
        next(call_count)

    monkeypatch.setattr(snapcraft_store_client, 'push', increase_call_count)
    push(context, '/some/file.snap', channel='mock')

    assert next(call_count) == 0


class SomeSpecificException(Exception):
    pass


@pytest.mark.parametrize('raises', (True, False))
def test_session(monkeypatch, raises):
    login_call_count = (n for n in range(0, 3))
    store_client_mock = MagicMock()
    monkeypatch.setattr('snapcraft.storeapi.StoreClient', lambda: store_client_mock)

    with tempfile.NamedTemporaryFile('w+') as fake_macaroon:
        def snapcraft_store_client_login_fake(store, config_fd):
            assert store == store_client_mock
            assert config_fd.name == fake_macaroon.name
            next(login_call_count)

        monkeypatch.setattr(snapcraft_store_client, 'login', snapcraft_store_client_login_fake)

        if raises:
            with pytest.raises(SomeSpecificException):
                with _session(fake_macaroon.name):
                    assert next(login_call_count) == 1
                    store_client_mock.logout.assert_not_called()
                    raise SomeSpecificException('Oh noes!')
        else:
            with _session(fake_macaroon.name):
                assert next(login_call_count) == 1
                store_client_mock.logout.assert_not_called()

        assert next(login_call_count) == 2  # login wasn't called again
        store_client_mock.logout.assert_called_once_with()
