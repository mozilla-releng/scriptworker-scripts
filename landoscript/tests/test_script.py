import pytest

from landoscript.script import async_main


@pytest.mark.asyncio
async def test_script(context):
    await async_main(context)
