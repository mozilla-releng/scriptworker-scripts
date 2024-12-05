import inspect
import logging
from asyncio import Future
from contextlib import nullcontext as does_not_raise
from textwrap import dedent

import pytest
import pytest_asyncio
from aiohttp.client_exceptions import ClientError

from bitrisescript import bitrise
from bitrisescript.exceptions import BitriseBuildException
from scriptworker_client.exceptions import TaskVerificationError


@pytest_asyncio.fixture
async def client():
    client = bitrise.BitriseClient()
    yield client
    await client.close()
    bitrise.BitriseClient._instance = None
    bitrise.BitriseClient._client = None


@pytest.mark.asyncio
async def test_bitrise_client(client):
    # Test new
    assert isinstance(client, bitrise.BitriseClient)
    assert client.base == bitrise.BITRISE_API_URL
    assert client.prefix == ""

    # Test set auth
    assert client.headers == {}
    client.set_auth("abc")
    assert client.headers == {"Authorization": "abc"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "app, response, expected",
    (
        pytest.param(
            "foo",
            [
                {"repo_slug": "foo", "slug": "123"},
                {"repo_slug": "other", "slug": "456"},
            ],
            "/apps/123",
            id="found",
        ),
        pytest.param(
            "foo",
            [
                {"repo_slug": "other", "slug": "456"},
            ],
            TaskVerificationError,
            id="missing",
        ),
        pytest.param(
            "foo",
            [
                {"repo_slug": "foo", "slug": "123"},
                {"repo_slug": "foo", "slug": "456"},
            ],
            TaskVerificationError,
            id="too_many",
        ),
    ),
)
async def test_bitrise_client_set_app_prefix(mocker, client, app, response, expected):
    mocker.patch.object(client, "request", return_value=response)
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            await client.set_app_prefix(app)
    else:
        await client.set_app_prefix(app)
        assert client.prefix == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prefix,endpoint,method,kwargs,raises,expected_args,expected_kwargs",
    (
        pytest.param(None, "/foo/bar", "get", {}, False, ("get", f"{bitrise.BITRISE_API_URL}/foo/bar"), {}, id="get"),
        pytest.param(None, "foo/bar", "get", {}, False, ("get", f"{bitrise.BITRISE_API_URL}/foo/bar"), {}, id="slash"),
        pytest.param("/app", "/foo/bar", "get", {}, False, ("get", f"{bitrise.BITRISE_API_URL}/app/foo/bar"), {}, id="prefix"),
        pytest.param(
            None, "/foo/bar", "post", {"json": {"data": 123}}, False, ("post", f"{bitrise.BITRISE_API_URL}/foo/bar"), {"json": {"data": 123}}, id="post"
        ),
        pytest.param(
            None,
            "/foo/bar",
            "post",
            {"json": {"data": 123}},
            ClientError,
            ("post", f"{bitrise.BITRISE_API_URL}/foo/bar"),
            {"json": {"data": 123}},
            id="raises",
        ),
    ),
)
async def test_bitrise_client_request(config, mocker, client, prefix, endpoint, method, kwargs, raises, expected_args, expected_kwargs):
    expected_kwargs.setdefault("headers", {}).update(
        {"Authorization": config["bitrise"]["access_token"]},
    )

    response = mocker.AsyncMock()
    response.status = 200
    m = mocker.patch.object(client._client, "request", return_value=Future())
    m.return_value.set_result(response)

    if prefix:
        client.prefix = prefix

    if raises:
        m.side_effect = raises
        with pytest.raises(raises):
            await client.request(endpoint, method, **kwargs)
    else:
        await client.request(endpoint, method, **kwargs)
        m.assert_called_once_with(*expected_args, **expected_kwargs)


@pytest.mark.asyncio
async def test_bitrise_client_request_with_pagination(responses, client):
    endpoint = "test"

    responses.get(f"{bitrise.BITRISE_API_URL}/{endpoint}", status=200, payload={"data": ["foo"], "paging": {"next": "abc"}})
    responses.get(f"{bitrise.BITRISE_API_URL}/{endpoint}?next=abc", status=200, payload={"data": ["bar"], "paging": {"next": "def"}})
    responses.get(f"{bitrise.BITRISE_API_URL}/{endpoint}?next=def", status=200, payload={"data": ["baz"], "paging": {}})

    result = await client.request(endpoint)
    assert result == ["foo", "bar", "baz"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "build_slug,status,expected",
    (
        pytest.param("foo", "success", {}, id="success"),
        pytest.param("foo", "error", BitriseBuildException, id="error"),
        pytest.param("foo", "aborted", BitriseBuildException, id="aborted"),
        pytest.param("foo", "unknown", BitriseBuildException, id="unknown"),
    ),
)
async def test_wait_for_build_finish(mocker, client, build_slug, status, expected):
    m = mocker.patch.object(client, "request", return_value=mocker.AsyncMock())
    side_effect = []
    num = 3
    for i in range(num):
        data = {"count": i + 1, "finished_at": None}
        if i == num - 1:
            data.update(
                {
                    "finished_at": True,
                    "status_text": status,
                }
            )
        side_effect.append(data)
    m.side_effect = side_effect

    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            await bitrise.wait_for_build_finish(build_slug, poll_interval=0.01)
    else:
        await bitrise.wait_for_build_finish(build_slug, poll_interval=0.01)
        assert m.call_count == 3


@pytest.mark.asyncio
async def test_download_artifacts(mocker, client):
    build_slug = "123"
    artifacts_dir = "artifacts"
    side_effect = []

    # First call will be to get artifact metadata
    artifacts = [{"title": "log.txt", "slug": "a"}, {"title": "build.zip", "slug": "b"}]
    side_effect.append(artifacts)

    # Then there will be one call per artifact to get the download url
    for artifact in artifacts:
        side_effect.append({"expiring_download_url": f"https://example.com/{artifact['title']}"})

    m_request = mocker.patch.object(client, "request", return_value=mocker.AsyncMock())
    m_request.side_effect = side_effect

    m_download = mocker.patch.object(bitrise, "download_file", return_value=mocker.AsyncMock())

    await bitrise.download_artifacts(build_slug, artifacts_dir)

    assert m_request.call_count == len(artifacts) + 1
    calls = m_request.call_args_list
    assert calls[0] == ((f"/builds/{build_slug}/artifacts",),)
    for i, artifact in enumerate(artifacts):
        assert calls[i + 1] == ((f"/builds/{build_slug}/artifacts/{artifact['slug']}",),)

    assert m_download.call_count == len(artifacts)
    calls = m_download.call_args_list
    for i, artifact in enumerate(artifacts):
        title = artifact["title"]
        assert calls[i] == ((f"https://example.com/{title}", f"{artifacts_dir}/{title}"),)


@pytest.mark.asyncio
async def test_download_log(mocker, client):
    build_slug = "123"
    artifacts_dir = "artifacts"
    log_url = "https://example.com/log.txt"

    m_request = mocker.patch.object(client, "request", return_value=mocker.AsyncMock())
    side_effect = []
    num = 3
    for i in range(num):
        data = {"count": i + 1, "is_archived": False}
        if i == num - 1:
            data.update(
                {
                    "is_archived": True,
                    "expiring_raw_log_url": log_url,
                }
            )
        side_effect.append(data)
    m_request.side_effect = side_effect
    m_download = mocker.patch.object(bitrise, "download_file", return_value=mocker.AsyncMock())

    await bitrise.download_log(build_slug, artifacts_dir, poll_interval=0.01)
    assert m_request.call_count == 3
    assert m_request.call_args == ((f"/builds/{build_slug}/log",),)
    assert m_download.call_count == 1
    assert m_download.call_args == ((log_url, f"{artifacts_dir}/bitrise.log"),)


@pytest.mark.asyncio
async def test_dump_perfherder_data(mocker, caplog):
    caplog.set_level(logging.INFO)
    artifacts_dir = "artifacts"

    # bitrise.log doesn't exist
    mock_is_file = mocker.patch.object(bitrise.Path, "is_file")
    mock_is_file.return_value = False
    await bitrise.dump_perfherder_data(artifacts_dir)
    assert "Not scanning for Perfherder data" in caplog.text

    # bitrise.log doesn't contain Perfherder data
    caplog.clear()
    mock_is_file.return_value = True
    mock_read_text = mocker.patch.object(bitrise.Path, "read_text")
    mock_read_text.return_value = dedent(
        """
    INFO does not contain
    DEBUG any perfherder data
    """
    ).strip()
    await bitrise.dump_perfherder_data(artifacts_dir)
    assert "Not scanning for Perfherder data" not in caplog.text
    assert "Found Perfherder data in" not in caplog.text

    # bitrise.log contains Perfherder data
    caplog.clear()
    mock_read_text.return_value = dedent(
        """
    INFO does contain
    PERFHERDER_DATA {"foo": "bar"}
    DEBUG perfherder data
    PERFHERDER_DATA {"baz": 1}
    """
    ).strip()
    await bitrise.dump_perfherder_data(artifacts_dir)
    assert "Not scanning for Perfherder data" not in caplog.text
    assert (
        dedent(
            """
        Found Perfherder data in artifacts/bitrise.log:
        PERFHERDER_DATA {"foo": "bar"}
        PERFHERDER_DATA {"baz": 1}
        """
        ).strip()
        in caplog.text
    )


@pytest.mark.asyncio
async def test_download_file(responses, tmp_path):
    url = "https://example.com/log.txt"
    body = "foobar"
    dest = tmp_path / "artifacts" / "log.txt"
    dest.parent.mkdir()

    responses.get(
        url,
        status=200,
        body=body,
    )

    await bitrise.download_file(url, dest)

    assert dest.exists()
    assert dest.read_text() == body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "build_response,expectation",
    (
        pytest.param({"status": "ok", "build_slug": "abc"}, does_not_raise(), id="ok"),
        pytest.param({"status": "fail", "build_slug": "abc"}, pytest.raises(Exception), id="fail"),
    ),
)
async def test_run_build(mocker, tmp_path, client, build_response, expectation):
    artifacts_dir = tmp_path / "artifacts"
    slug = build_response.get("build_slug", "abc")
    wf_id = "test"

    m_request = mocker.patch.object(client, "request", return_value=mocker.AsyncMock())
    m_request.return_value = build_response

    m_wait = mocker.patch.object(bitrise, "wait_for_build_finish", return_value=mocker.AsyncMock())
    m_dl_artifacts = mocker.patch.object(bitrise, "download_artifacts", return_value=mocker.AsyncMock())
    m_dl_log = mocker.patch.object(bitrise, "download_log", return_value=mocker.AsyncMock())

    assert not artifacts_dir.is_dir()
    with expectation:
        await bitrise.run_build(artifacts_dir, wf_id, foo="bar")

        m_request.assert_called_once_with(
            "/builds", method="post", json={"hook_info": {"type": "bitrise"}, "build_params": {"foo": "bar", "workflow_id": wf_id}}
        )
        m_wait.assert_called_once_with(slug)
        m_dl_artifacts.assert_called_once_with(slug, f"{artifacts_dir}/{wf_id}")
        m_dl_log.assert_called_once_with(slug, f"{artifacts_dir}/{wf_id}")

    assert artifacts_dir.is_dir()


@pytest.mark.asyncio
async def test_get_running_builds(responses):
    workflow_id = "wkflw"
    responses.get(f"{bitrise.BITRISE_API_URL}/builds?workflow={workflow_id}&status=0", status=200, payload={"data": ["foo"], "paging": {}})
    result = await bitrise.get_running_builds(workflow_id)
    assert result == ["foo"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "running_builds,build_params,expected",
    (
        pytest.param([], {}, None, id="success empty None"),
        pytest.param([{"original_build_params": {"foo": "bar"}}], {"foo": "yeet"}, None, id="success non-empty None"),
        pytest.param([{"original_build_params": {"foo": "bar"}, "slug": {"a": "b"}}], {"foo": "bar"}, {"a": "b"}, id="success non-empty Found"),
    ),
)
async def test_find_running_build(responses, running_builds, build_params, expected):
    result = bitrise.find_running_build(running_builds, build_params)
    assert result == expected


@pytest.mark.asyncio
async def test_abort_build(mocker, client):
    build_slug = "123"

    m_request = mocker.patch.object(client, "request", return_value=mocker.AsyncMock())

    await bitrise.abort_build(build_slug, "out of baguettes")

    m_request.assert_called_once_with(
        f"/builds/{build_slug}/abort", method="post", json={"abort_reason": "out of baguettes", "abort_with_success": False, "skip_notifications": False}
    )
