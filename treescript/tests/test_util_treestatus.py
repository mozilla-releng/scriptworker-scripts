import pytest

import treescript.util.treestatus as tstatus


async def noop_async(*args, **kwargs):
    pass


# check_treestatus {{{1
@pytest.mark.parametrize("status, expected", (("open", True), ("closed", False), ("approval required", True)))
@pytest.mark.asyncio
async def test_check_treestatus(status, mocker, expected):
    """check_treestatus returns False for a closed tree, and True otherwise."""
    config = {"treestatus_base_url": "url", "work_dir": "foo"}
    treestatus = {"result": {"message_of_the_day": "", "reason": "", "status": status, "tree": "mozilla-central"}}
    mocker.patch.object(tstatus, "download_file", new=noop_async)
    mocker.patch.object(tstatus, "get_short_source_repo", return_value="tree")
    mocker.patch.object(tstatus, "load_json_or_yaml", return_value=treestatus)
    assert await tstatus.check_treestatus(config, {}) == expected
