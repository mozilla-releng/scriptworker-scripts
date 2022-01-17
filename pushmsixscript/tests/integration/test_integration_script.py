import json
import os
import tempfile
from unittest.mock import Mock

import pytest
import requests
import requests_mock
from scriptworker_client.utils import makedirs

from pushmsixscript import manifest, microsoft_store
from pushmsixscript.script import main


@pytest.mark.parametrize(
    "config, channel, raises, requests_call_count",
    (
        (
            {
                "push_to_store": False,
                "login_url": "https://fake-login.com",
                "token_resource": "https://fake-token-resource.com",
                "store_url": "https://fake-store.com/",
                "request_timeout_seconds": 30,
                "application_ids": {
                    "release": "123a",
                },
                "tenant_id": "mock-tenant-id",
                "client_id": "mock-client-id",
                "client_secret": "mock-client-secret",
            },
            "release",
            False,
            0,
        ),
        (
            {
                "push_to_store": True,
                "login_url": "https://fake-login.com",
                "token_resource": "https://fake-token-resource.com",
                "store_url": "https://fake-store.com/",
                "request_timeout_seconds": 30,
                "application_ids": {
                    "release": "123b",
                },
                "tenant_id": "mock-tenant-id",
                "client_id": "mock-client-id",
                "client_secret": "mock-client-secret",
            },
            "release",
            False,
            8,
        ),
    ),
)
def test_script_can_push_msix(monkeypatch, config, channel, raises, requests_call_count):
    task = {
        "dependencies": ["some_msix_build_taskId"],
        "scopes": [f"project:releng:microsoftstore:{channel}"],
        "payload": {
            "channel": channel,
            "upstreamArtifacts": [
                {"paths": ["public/build/target.x86.store.msix", "public/build/target.x64.store.msix"], "taskId": "some_msix_build_taskId", "taskType": "build"}
            ],
        },
    }

    headers = {}
    login_url = config["login_url"]
    tenant_id = config["tenant_id"]
    application_id = config["application_ids"][channel]
    submission_id = 888
    upload_url = "https://some/url"
    session_mocked_response = {"access_token": "mocked-access-token"}
    create_mocked_response = {"id": 888, "fileUploadUrl": "https://some/url"}
    mocked_response = {}
    status_code = 200
    with requests_mock.Mocker() as m:

        url = f"{login_url}/{tenant_id}/oauth2/token"
        m.post(url, headers=headers, json=session_mocked_response, status_code=status_code)
        url = microsoft_store._store_url(config, f"{application_id}")
        m.get(url, headers=headers, json=mocked_response, status_code=status_code)
        url = microsoft_store._store_url(config, f"{application_id}/submissions/{submission_id}")
        m.delete(url, headers=headers)
        url = microsoft_store._store_url(config, f"{application_id}/submissions")
        m.post(url, headers=headers, json=create_mocked_response, status_code=status_code)
        url = microsoft_store._store_url(config, f"{application_id}/submissions/{submission_id}")
        m.put(url, headers=headers, json=mocked_response, status_code=status_code)
        m.put(upload_url, headers=headers, json=mocked_response, status_code=status_code)
        url = microsoft_store._store_url(config, f"{application_id}/submissions/{submission_id}/commit")
        m.post(url, headers=headers, json=mocked_response, status_code=status_code)
        url = microsoft_store._store_url(config, f"{application_id}/submissions/{submission_id}/status")
        m.get(url, headers=headers, json=mocked_response, status_code=status_code)

        manifest.verify_msix = Mock(return_value=True)

        with tempfile.TemporaryDirectory() as work_dir:
            config["work_dir"] = work_dir

            with open(os.path.join(work_dir, "task.json"), "w") as task_file:
                json.dump(task, task_file)

            msix_artifact_dir = os.path.join(work_dir, "cot/some_msix_build_taskId/public/build/")
            makedirs(msix_artifact_dir)
            for arch in ["x86", "x64"]:
                msix_artifact_path = os.path.join(msix_artifact_dir, f"target.{arch}.store.msix")
                with open(msix_artifact_path, "w") as msix_file:
                    msix_file.write(" ")

            # config_file is not put in the TemporaryDirectory() (like the others), because it usually lives
            # elsewhere on the filesystem
            with tempfile.NamedTemporaryFile("w+") as config_file:
                json.dump(config, config_file)
                config_file.seek(0)

                if raises:
                    with pytest.raises(requests.exceptions.HTTPError):
                        main(config_path=config_file.name)
                else:
                    main(config_path=config_file.name)
                    assert m.call_count == requests_call_count
