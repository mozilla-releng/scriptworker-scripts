import os
import os.path
from collections import namedtuple
from unittest import mock

import pytest
from conftest import TEST_DATA_DIR

import signingscript.rcodesign as rcodesign


@pytest.mark.asyncio
async def test_rcodesign_notarize(mocker, context):
    path = os.path.join(TEST_DATA_DIR, "appletest.tar.gz")
    execute = mock.AsyncMock()
    execute.side_effect = [(0, ["created submission ID: 123"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)

    submission_id = await rcodesign.rcodesign_notarize(path, context.config["apple_notarization_configs"])
    assert submission_id == "123"
    execute.assert_awaited_once_with([
        "rcodesign",
        "notary-submit",
        "--api-key-path",
        context.config["apple_notarization_configs"],
        path,
    ])


@pytest.mark.asyncio
async def test_rcodesign_notarize_staple(mocker, context):
    path = os.path.join(TEST_DATA_DIR, "appletest.tar.gz")
    execute = mock.AsyncMock()
    execute.side_effect = [(0, ["created submission ID: 123"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)

    submission_id = await rcodesign.rcodesign_notarize(path, context.config["apple_notarization_configs"], True)
    assert submission_id == "123"
    execute.assert_awaited_once_with([
        "rcodesign",
        "notary-submit",
        "--staple",
        "--api-key-path",
        context.config["apple_notarization_configs"],
        path,
    ])


@pytest.mark.asyncio
async def test_rcodesign_notarize_failure(mocker, context):
    path = os.path.join(TEST_DATA_DIR, "appletest.tar.gz")
    execute = mock.AsyncMock()
    execute.side_effect = [(1, ["errror blah"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)

    with pytest.raises(rcodesign.RCodesignError):
        await rcodesign.rcodesign_notarize(path, context.config["apple_notarization_configs"])


@pytest.mark.asyncio
async def test_rcodesign_notary_wait(mocker):
    execute = mock.AsyncMock()
    execute.side_effect = [(0, ["poll state after 1s: InProgress", "poll state after 108s: Accepted"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)
    creds_path = "/foo/bar"
    submission_id = "123"
    await rcodesign.rcodesign_notary_wait(submission_id, creds_path)
    execute.assert_awaited_once_with([
        "rcodesign",
        "notary-wait",
        "--api-key-path",
        creds_path,
        submission_id,
    ])
    execute.reset_mock()
    execute.side_effect = [(0, ["weird logs, but no errors"])]
    await rcodesign.rcodesign_notary_wait(submission_id, creds_path)
    execute.assert_awaited_once_with([
        "rcodesign",
        "notary-wait",
        "--api-key-path",
        creds_path,
        submission_id,
    ])


@pytest.mark.asyncio
async def test_rcodesign_notary_wait_fail(mocker):
    execute = mock.AsyncMock()
    execute.side_effect = [(1, ["mock poll failure complete"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)
    creds_path = "/foo/bar"
    submission_id = "123"
    with pytest.raises(rcodesign.RCodesignError):
        await rcodesign.rcodesign_notary_wait(submission_id, creds_path)


@pytest.mark.asyncio
async def test_rcodesign_notary_wait_check_fail(mocker):
    execute = mock.AsyncMock()
    execute.side_effect = [(0, ["poll state after 100s: Invalid"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)
    creds_path = "/foo/bar"
    submission_id = "123"
    with pytest.raises(rcodesign.RCodesignError):
        await rcodesign.rcodesign_notary_wait(submission_id, creds_path)


@pytest.mark.asyncio
async def test_rcodesign_staple(mocker):
    execute = mock.AsyncMock()
    execute.side_effect = [(0, ["staple complete"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)
    path = "/foo/bar"
    await rcodesign.rcodesign_staple(path)
    execute.assert_awaited_once_with(["rcodesign", "staple", path])


@pytest.mark.asyncio
async def test_rcodesign_staple_fail(mocker):
    execute = mock.AsyncMock()
    execute.side_effect = [(1, ["staple complete"])]
    mocker.patch.object(rcodesign, "_execute_command", execute)
    with pytest.raises(rcodesign.RCodesignError):
        await rcodesign.rcodesign_staple("/foo/bar")


@pytest.mark.asyncio
async def test_find_submission_id():
    expected = "321123"
    logs = ["foo", "bar", "created submission ID: 321123", "baz"]
    result = rcodesign.find_submission_id(logs)
    assert result == expected


@pytest.mark.asyncio
async def test_find_submission_id_fail():
    logs = ["foo", "created submission ID: 4564", "created submission ID: 321123", "baz"]
    with pytest.raises(rcodesign.RCodesignError):
        rcodesign.find_submission_id(logs)


def mock_async_generator(*values):
    vals = [*values]
    async def func():
        return vals.pop(0)
    return func


def mock_sync_generator(*values):
    vals = [*values]
    def func():
        return vals.pop(0)
    return func


@pytest.mark.asyncio
async def test_execute_command(mocker):
    async def mock_create_subprocess_exec(*args, **kwargs):
        Subprocess = namedtuple("subprocess", ["stdout", "stderr", "wait"])
        Stream = namedtuple("Stream", ["readline", "at_eof"])
        generic_stream = Stream(mock_async_generator(b"hello", b"err", b"", b""), mock_sync_generator(False, False, True, True))
        return Subprocess(generic_stream, generic_stream, mock_async_generator(96))

    mocker.patch.object(rcodesign.asyncio, "create_subprocess_exec", mock_create_subprocess_exec)
    exitcode, output = await rcodesign._execute_command(["echo", "1"])
    assert exitcode == 96
    assert len(output) > 1
    assert output == ["hello", "err"]
