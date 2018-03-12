import pytest

from scriptworker import client
from unittest.mock import MagicMock

from pushsnapscript.script import async_main


@pytest.mark.asyncio
async def test_hello_world(capsys, monkeypatch):
    monkeypatch.setattr(client, 'get_task', lambda _: {})
    context = MagicMock()

    await async_main(context)

    captured = capsys.readouterr()
    assert captured.out == 'Hello World!\n'
    assert captured.err == ''
