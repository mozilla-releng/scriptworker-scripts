import pytest

from landoscript.script import async_main


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    (
        pytest.param(
            {
            },
            id="one_file",
        ),
    ),
)
async def test_version_bump(context):
    await async_main(context)
