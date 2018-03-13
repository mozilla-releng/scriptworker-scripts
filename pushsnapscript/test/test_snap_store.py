import pytest
import os
import tempfile

from unittest.mock import MagicMock

from pushsnapscript.snap_store import snapcraft_store_client, push, _craft_credentials_file

SNAPCRAFT_SAMPLE_CONFIG = '''[login.ubuntu.com]
macaroon = SomeBase64
unbound_discharge = SomeOtherBase64
email = release@m.c
'''

SNAPCRAFT_SAMPLE_CONFIG_BASE64 = 'W2xvZ2luLnVidW50dS5jb21dCm1hY2Fyb29uID0gU29tZUJhc2U2NAp1bmJvdW5kX\
2Rpc2NoYXJnZSA9IFNvbWVPdGhlckJhc2U2NAplbWFpbCA9IHJlbGVhc2VAbS5jCg=='


@pytest.mark.parametrize('channel', ('edge', 'candidate'))
def test_push(monkeypatch, channel):
    call_count = (n for n in range(0, 2))

    context = MagicMock()
    context.config = {'base64_macaroons_configs': {channel: SNAPCRAFT_SAMPLE_CONFIG_BASE64}}

    with tempfile.TemporaryDirectory() as d:
        def snapcraft_store_client_push_fake(snap_file_path, channel):
            # This function can't be a regular mock because of the following check:
            assert os.getcwd() == d     # Push must be done from the work_dir

            assert snap_file_path == '/some/file.snap'
            assert channel == channel
            next(call_count)

        context.config['work_dir'] = d
        monkeypatch.setattr(snapcraft_store_client, 'push', snapcraft_store_client_push_fake)
        push(context, '/some/file.snap', channel)

        assert os.getcwd() != d

    assert next(call_count) == 1


def test_push_early_return_if_not_allowed(monkeypatch):
    call_count = (n for n in range(0, 2))

    context = MagicMock()

    def increase_call_count(_, __):
        next(call_count)

    monkeypatch.setattr(snapcraft_store_client, 'push', increase_call_count)
    push(context, '/some/file.snap', channel='mock')

    assert next(call_count) == 0


@pytest.mark.parametrize('channel', ('edge', 'candidate'))
def test_craft_credentials_file(channel):
    context = MagicMock()
    context.config = {'base64_macaroons_configs': {channel: SNAPCRAFT_SAMPLE_CONFIG_BASE64}}

    with tempfile.TemporaryDirectory() as d:
        context.config['work_dir'] = d
        _craft_credentials_file(context, channel)
        with open(os.path.join(d, '.snapcraft', 'snapcraft.cfg')) as f:
            assert f.read() == SNAPCRAFT_SAMPLE_CONFIG
