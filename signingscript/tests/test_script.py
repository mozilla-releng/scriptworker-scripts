import os
import shutil

from aiohttp import ClientResponseError
import pytest
import yarl
from scriptworker.utils import json
from winsign.makemsix import base64

from signingscript import sign
from signingscript.script import async_main

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def setup_artifacts(work_dir: str, artifacts: list[str], taskid: str):
    taskdir = os.path.join(work_dir, "cot", taskid)
    os.makedirs(taskdir)
    for a in artifacts:
        shutil.copy(os.path.join(DATA_DIR, a), os.path.join(taskdir, a))


def assert_sign_data_req(req, keyid):
    assert "Authorization" in req.kwargs["headers"]
    assert "Content-Length" in req.kwargs["headers"]
    assert req.kwargs["headers"]["Content-Type"] == "application/json"
    assert "data" in req.kwargs
    data = json.loads(req.kwargs["data"].read().decode("utf-8"))
    for entry in data:
        assert entry["keyid"] == keyid


def assert_sign_hash_req(req, keyid):
    assert "Authorization" in req.kwargs["headers"]
    assert "Content-Length" in req.kwargs["headers"]
    assert req.kwargs["headers"]["Content-Type"] == "application/json"
    assert "data" in req.kwargs
    data = json.loads(req.kwargs["data"].read().decode("utf-8"))
    for entry in data:
        assert entry["keyid"] == keyid


def make_base64_encoded_string(length: int) -> str:
    """Returns the base64-encoded version of a string of the given length
    as a string."""
    # Make a string of the required length
    input_str = "{:<" + str(length) + "}"
    input_str = input_str.format("A")
    # Encode it into bytes, because that's what b64encode requires
    bytestr = input_str.encode()
    # base64 encode it
    encoded = base64.b64encode(bytestr)
    # and finally, convert the bytes that are returned back to a str
    return encoded.decode("utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "formats,server,keyid,files,method",
    [
        pytest.param(
            ["autograph_gpg"],
            "https://prod",
            "gpgkey",
            ["target.tar.gz"],
            "data",
            id="autograph_gpg",
        ),
        pytest.param(
            ["stage_autograph_gpg"],
            "https://stage",
            "gpgkey",
            ["target.tar.gz"],
            "data",
            id="stage_autograph_gpg",
        ),
        # TODO: test for multiple files at once
        # TODO: tests for multiple formats at once, like we do in prod
    ],
)
async def test_signing(aioresponses, context, formats: list[str], server: str, keyid: str, files: list[str], method: str):
    taskid = "faketask"
    setup_artifacts(context.config["work_dir"], files, taskid)
    context.task["payload"] = {
        "upstreamArtifacts": [
            {
                "formats": formats,
                "paths": files,
                "taskId": taskid,
                "taskType": "build",
            },
        ],
    }

    url = yarl.URL(f"{server}/sign/{method}")
    aioresponses.post(
        url,
        status=200,
        payload=[
            {
                "signature": "foo",
            },
        ],
    )

    await async_main(context)

    assert len(aioresponses.requests) == 1
    reqs = aioresponses.requests[("POST", url)]
    assert len(reqs) == 1
    assert_sign_data_req(reqs[0], keyid)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "formats,server,keyid,files,method",
    [
        pytest.param(
            ["widevine"],
            "https://prod",
            "widevinekey",
            ["widevine.tar.gz"],
            "hash",
            id="widevine",
        ),
        pytest.param(
            ["stage_widevine"],
            "https://stage",
            "widevinekey",
            ["widevine.zip"],
            "hash",
            id="stage_widevine",
        ),
        # TODO: test for multiple files at once
        # TODO: tests for multiple formats at once, like we do in prod
    ],
)
async def test_widevine_signing(mocker, aioresponses, context, formats: list[str], server: str, keyid: str, files: list[str], method: str):
    taskid = "faketask"
    setup_artifacts(context.config["work_dir"], files, taskid)
    context.task["payload"] = {
        "upstreamArtifacts": [
            {
                "formats": formats,
                "paths": files,
                "taskId": taskid,
                "taskType": "build",
            },
        ],
    }

    url = yarl.URL(f"{server}/sign/{method}")
    # two calls because there are two widevine signing files
    # in our test files
    for _ in range(0, 2):
        aioresponses.post(
            url,
            status=200,
            payload=[
                {
                    "signature": base64.b64encode(b"foo").decode(),
                },
            ],
        )

    class FakeWidevine(object):
        def generate_widevine_hash(self, *args, **kwargs):
            return b"blah"

        def generate_widevine_signature(self, *args, **kwargs):
            return b"blah"

    mocker.patch.object(sign, "widevine", FakeWidevine)

    await async_main(context)

    assert len(aioresponses.requests) == 1
    reqs = aioresponses.requests[("POST", url)]
    assert len(reqs) == 2
    assert_sign_data_req(reqs[0], keyid)
    assert_sign_data_req(reqs[1], keyid)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "formats,server",
    [
        pytest.param(
            ["autograph_gpg"],
            "https://prod",
            id="autograph_gpg",
        ),
    ],
)
async def test_gpg_signing_fail(aioresponses, context, formats: list[str], server: str):
    taskid = "faketask"
    setup_artifacts(context.config["work_dir"], ["target.tar.gz"], taskid)
    context.task["payload"] = {
        "upstreamArtifacts": [
            {
                "formats": formats,
                "paths": ["target.tar.gz"],
                "taskId": taskid,
                "taskType": "build",
            },
        ],
    }

    url = yarl.URL(f"{server}/sign/data")
    # we have 3 hardcoded retries
    # TODO: we should remove sleep time for retries during tests
    for _ in range(0, 3):
        aioresponses.post(
            url,
            status=400,
        )

    try:
        await async_main(context)
        assert False, "should've raised ClientResponseError"
    except ClientResponseError:
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "formats,server,keyid",
    [
        pytest.param(
            ["autograph_hash_only_mar384"],
            "https://prod",
            "markey",
            id="autograph_hash_only_mar384",
        ),
        pytest.param(
            ["stage_autograph_hash_only_mar384"],
            "https://stage",
            "markey",
            id="stage_autograph_hash_only_mar384",
        ),
    ],
)
async def test_mar_signing(mocker, aioresponses, context, formats: list[str], server: str, keyid: str):
    taskid = "faketask"
    setup_artifacts(context.config["work_dir"], ["partial1.mar"], taskid)
    context.task["payload"] = {
        "upstreamArtifacts": [
            {
                "formats": formats,
                "paths": ["partial1.mar"],
                "taskId": taskid,
                "taskType": "build",
            },
        ],
    }

    # Unfortunately, mocking `verify_mar_signature` cannot be avoided, because
    # we can't make real MAR signatures in tests.
    mocker.patch.object(sign, "verify_mar_signature", lambda *_: True)

    url = yarl.URL(f"{server}/sign/hash")
    aioresponses.post(
        url,
        status=200,
        payload=[
            {
                "signature": make_base64_encoded_string(512),
            }
        ],
    )

    await async_main(context)

    assert len(aioresponses.requests) == 1
    reqs = aioresponses.requests[("POST", url)]
    assert len(reqs) == 1
    assert_sign_hash_req(reqs[0], keyid)
