from pathlib import Path
import pytest
import re

from bitrisescript.bitrise import BITRISE_API_URL
from bitrisescript.script import async_main


@pytest.mark.asyncio
async def test_main_run_workflow(responses, tmp_path, config):
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    artifact_dir = work_dir / "artifacts"
    config["work_dir"] = str(work_dir)
    config["artifact_dir"] = str(artifact_dir)

    app = "project"
    app_slug = "abc"
    base_artifact_url = "https://example.com"
    log_url = f"{base_artifact_url}/log.txt"
    workflows = ["build", "test"]

    task = {
        "dependencies": ["dependency-task-id"],
        "scopes": ["test:prefix:app:project"],
        "payload": {},
    }
    task["scopes"].extend([f"test:prefix:workflow:{w}" for w in workflows])

    responses.get(f"{BITRISE_API_URL}/apps", status=200, payload={"data": [{"repo_slug": app, "slug": app_slug}]})
    responses.get(re.compile(f"^{BITRISE_API_URL}/builds?.*"), status=200, payload={"data": [{"original_build_params": {"foo": "bar"}}]}, repeat=True)

    for i, workflow in enumerate(workflows):
        artifact_url = f"{base_artifact_url}/{workflow}.zip"
        build_slug = str(i) * 3
        artifact_slug = chr(i + 96) * 3

        responses.post(f"{BITRISE_API_URL}/apps/{app_slug}/builds", status=200, payload={"status": "ok", "build_slug": build_slug})
        responses.get(f"{BITRISE_API_URL}/apps/{app_slug}/builds/{build_slug}/log", status=200, payload={"is_archived": True, "expiring_raw_log_url": log_url})
        responses.get(log_url, status=200, body="log")
        responses.get(f"{BITRISE_API_URL}/apps/{app_slug}/builds/{build_slug}", status=200, payload={"data": {"finished_at": "now", "status_text": "success"}})
        responses.get(
            f"{BITRISE_API_URL}/apps/{app_slug}/builds/{build_slug}/artifacts",
            status=200,
            payload={"data": [{"title": f"{workflow}.zip", "slug": artifact_slug}]},
        )
        responses.get(
            f"{BITRISE_API_URL}/apps/{app_slug}/builds/{build_slug}/artifacts/{artifact_slug}",
            status=200,
            payload={"data": {"expiring_download_url": artifact_url}},
        )
        responses.get(artifact_url, status=200, body=workflow)

    await async_main(config, task)

    for workflow in workflows:
        artifact = artifact_dir / workflow / f"{workflow}.zip"
        assert artifact.is_file()
        assert artifact.read_text() == workflow

        log = artifact_dir / workflow / "bitrise.log"
        assert log.is_file()
        assert log.read_text() == "log"
