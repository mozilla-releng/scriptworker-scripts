import tempfile
from unittest.mock import patch

import pytest
import requests
import requests_mock

from pushmsixscript import microsoft_store
from scriptworker_client.exceptions import TaskError, TimeoutError

CONFIG = {
    "push_to_store": True,
    "login_url": "https://fake-login.com",
    "token_resource": "https://fake-token-resource.com",
    "store_url": "https://fake-store.com/",
    "request_timeout_seconds": 30,
    "tenant_id": "mock-tenant-id",
    "client_id": "mock-client-id",
    "client_secret": "mock-client-secret",
    "application_ids": {"mock": "1234"},
}


@pytest.mark.parametrize(
    "status_code, raises",
    (
        (200, False),
        (404, True),
        (503, True),
    ),
)
def test_store_session(status_code, raises):
    login_url = CONFIG["login_url"]
    tenant_id = CONFIG["tenant_id"]
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
    expected_access_token = "mock-access-token"
    mocked_response = {"access_token": expected_access_token}

    with requests_mock.Mocker() as m:
        url = f"{login_url}/{tenant_id}/oauth2/token"
        m.post(url, headers=headers, json=mocked_response, status_code=status_code)
        if raises:
            with pytest.raises(requests.exceptions.HTTPError):
                token = microsoft_store._store_session(CONFIG)
        else:
            token = microsoft_store._store_session(CONFIG)
            assert token == expected_access_token


@pytest.mark.parametrize(
    "status_code, pending, raises, exc",
    (
        (200, True, True, TaskError),
        (200, False, False, None),
        (404, False, True, requests.exceptions.HTTPError),
        (503, False, True, requests.exceptions.HTTPError),
    ),
)
def test_check_for_pending_submission(status_code, pending, raises, exc):
    headers = {}
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    submission_to_remove = 43
    if pending:
        mocked_response = {"pendingApplicationSubmission": {"id": submission_to_remove}}
    else:
        mocked_response = {}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(CONFIG, f"{application_id}")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_to_remove}")
            m.delete(url, headers=headers)

            if raises:
                with pytest.raises(exc):
                    microsoft_store._check_for_pending_submission(CONFIG, channel, session, headers)
            else:
                microsoft_store._check_for_pending_submission(CONFIG, channel, session, headers)


@pytest.mark.parametrize(
    "status_code, raises",
    (
        (200, False),
        (404, True),
        (503, True),
    ),
)
def test_create_submission(status_code, raises):
    headers = {}
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    mocked_response = {"id": 888, "fileUploadUrl": "https://some/url"}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions")
            m.post(url, headers=headers, json=mocked_response, status_code=status_code)
            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    (submission_request, enc) = microsoft_store._create_submission(CONFIG, channel, session, headers)
            else:
                (submission_request, enc) = microsoft_store._create_submission(CONFIG, channel, session, headers)
                assert submission_request == mocked_response
                assert enc == "utf-8"


@pytest.mark.parametrize(
    "status_code, raises, publish_mode",
    (
        (200, False, None),
        (200, False, "Immediate"),
        (404, True, None),
        (503, True, None),
    ),
)
def test_update_submission(status_code, raises, publish_mode):
    headers = {}
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    submission_request = {"id": 888, "fileUploadUrl": "https://some/url", "applicationPackages": [{"minimumDirectXVersion": 1, "minimumSystemRam": 1024}]}
    submission_id = submission_request["id"]
    upload_url = submission_request["fileUploadUrl"]
    mocked_response = {"status": "OK"}
    encoding = "utf-8"
    with tempfile.NamedTemporaryFile(mode="wb") as f:
        f.write(b"hello there")
        with requests.Session() as session:
            with requests_mock.Mocker() as m:
                url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}")
                m.put(url, headers=headers, json=mocked_response, status_code=status_code)
                m.put(upload_url, headers=headers, json=mocked_response, status_code=200)
                with patch.object(microsoft_store, "BlobClient"):
                    if raises:
                        with pytest.raises(requests.exceptions.HTTPError):
                            microsoft_store._update_submission(CONFIG, channel, session, submission_request, headers, [f.name], publish_mode, encoding)
                    else:
                        microsoft_store._update_submission(CONFIG, channel, session, submission_request, headers, [f.name], publish_mode, encoding)


@pytest.mark.parametrize(
    "config, channel, submission_request, file_paths, publish_mode, expected_submission_request, expected_upload_file_names",
    (
        (
            {},
            "beta",
            {},
            [],
            None,
            {
                "allowTargetFutureDeviceFamilies": {
                    "Desktop": True,
                    "Holographic": False,
                    "Mobile": False,
                    "Xbox": False,
                },
                "listings": {
                    "en-us": {
                        "baseListing": {
                            "copyrightAndTrademarkInfo": "",
                            "description": "Description",
                            "features": [],
                            "images": [],
                            "keywords": [],
                            "licenseTerms": "",
                            "privacyPolicy": "",
                            "recommendedHardware": [],
                            "releaseNotes": "",
                            "supportContact": "",
                            "title": "Firefox Nightly",
                            "websiteUrl": "",
                        },
                    },
                },
            },
            {},
        ),
        (
            {},
            "beta",
            {
                "applicationCategory": "NotSet",
            },
            [],
            None,
            {
                "allowTargetFutureDeviceFamilies": {
                    "Desktop": True,
                    "Holographic": False,
                    "Mobile": False,
                    "Xbox": False,
                },
                "applicationCategory": "Productivity",
                "listings": {
                    "en-us": {
                        "baseListing": {
                            "copyrightAndTrademarkInfo": "",
                            "description": "Description",
                            "features": [],
                            "images": [],
                            "keywords": [],
                            "licenseTerms": "",
                            "privacyPolicy": "",
                            "recommendedHardware": [],
                            "releaseNotes": "",
                            "supportContact": "",
                            "title": "Firefox Nightly",
                            "websiteUrl": "",
                        },
                    },
                },
            },
            {},
        ),
        (
            {},
            "beta",
            {
                "listings": {"dummy-locale": {"dummy key": "dummy value"}},
            },
            [],
            None,
            {
                "allowTargetFutureDeviceFamilies": {
                    "Desktop": True,
                    "Holographic": False,
                    "Mobile": False,
                    "Xbox": False,
                },
                "listings": {"dummy-locale": {"dummy key": "dummy value"}},
            },
            {},
        ),
        (
            {},
            "beta",
            {
                "allowTargetFutureDeviceFamilies": {"dummy key": "dummy value"},
            },
            [],
            None,
            {
                "allowTargetFutureDeviceFamilies": {"dummy key": "dummy value"},
                "listings": {
                    "en-us": {
                        "baseListing": {
                            "copyrightAndTrademarkInfo": "",
                            "description": "Description",
                            "features": [],
                            "images": [],
                            "keywords": [],
                            "licenseTerms": "",
                            "privacyPolicy": "",
                            "recommendedHardware": [],
                            "releaseNotes": "",
                            "supportContact": "",
                            "title": "Firefox Nightly",
                            "websiteUrl": "",
                        },
                    },
                },
            },
            {},
        ),
        (
            {},
            "beta",
            {},
            [],
            "Immediate",
            {
                "allowTargetFutureDeviceFamilies": {
                    "Desktop": True,
                    "Holographic": False,
                    "Mobile": False,
                    "Xbox": False,
                },
                "listings": {
                    "en-us": {
                        "baseListing": {
                            "copyrightAndTrademarkInfo": "",
                            "description": "Description",
                            "features": [],
                            "images": [],
                            "keywords": [],
                            "licenseTerms": "",
                            "privacyPolicy": "",
                            "recommendedHardware": [],
                            "releaseNotes": "",
                            "supportContact": "",
                            "title": "Firefox Nightly",
                            "websiteUrl": "",
                        },
                    },
                },
                "targetPublishMode": "Immediate",
            },
            {},
        ),
        (
            {},
            "beta",
            {
                "applicationPackages": [
                    {"fileStatus": "PendingUpload"},
                    {"fileStatus": "PendingUpload"},
                ]
            },
            [],
            None,
            {
                "allowTargetFutureDeviceFamilies": {
                    "Desktop": True,
                    "Holographic": False,
                    "Mobile": False,
                    "Xbox": False,
                },
                "applicationPackages": [
                    {"fileStatus": "PendingDelete"},
                    {"fileStatus": "PendingDelete"},
                ],
                "listings": {
                    "en-us": {
                        "baseListing": {
                            "copyrightAndTrademarkInfo": "",
                            "description": "Description",
                            "features": [],
                            "images": [],
                            "keywords": [],
                            "licenseTerms": "",
                            "privacyPolicy": "",
                            "recommendedHardware": [],
                            "releaseNotes": "",
                            "supportContact": "",
                            "title": "Firefox Nightly",
                            "websiteUrl": "",
                        },
                    },
                },
            },
            {},
        ),
        (
            {},
            "beta",
            {
                "applicationPackages": [
                    {
                        "fileName": "some-old.msix",
                        "fileStatus": "PendingUpload",
                        "minimumDirectXVersion": 1,
                        "minimumSystemRam": 2,
                    }
                ],
            },
            [
                "win32.msix",
                "win64.msix",
                "win64-aarch64.msix",
            ],
            None,
            {
                "allowTargetFutureDeviceFamilies": {
                    "Desktop": True,
                    "Holographic": False,
                    "Mobile": False,
                    "Xbox": False,
                },
                "applicationPackages": [
                    {
                        "fileName": "some-old.msix",
                        "fileStatus": "PendingDelete",
                        "minimumDirectXVersion": 1,
                        "minimumSystemRam": 2,
                    },
                    {
                        "fileName": "target.store.240101.1.msix",
                        "fileStatus": "PendingUpload",
                        "minimumDirectXVersion": 1,
                        "minimumSystemRam": 2,
                    },
                    {
                        "fileName": "target.store.240101.2.msix",
                        "fileStatus": "PendingUpload",
                        "minimumDirectXVersion": 1,
                        "minimumSystemRam": 2,
                    },
                    {
                        "fileName": "target.store.240101.3.msix",
                        "fileStatus": "PendingUpload",
                        "minimumDirectXVersion": 1,
                        "minimumSystemRam": 2,
                    },
                ],
                "listings": {
                    "en-us": {
                        "baseListing": {
                            "copyrightAndTrademarkInfo": "",
                            "description": "Description",
                            "features": [],
                            "images": [],
                            "keywords": [],
                            "licenseTerms": "",
                            "privacyPolicy": "",
                            "recommendedHardware": [],
                            "releaseNotes": "",
                            "supportContact": "",
                            "title": "Firefox Nightly",
                            "websiteUrl": "",
                        },
                    },
                },
            },
            {
                "win32.msix": "target.store.240101.1.msix",
                "win64.msix": "target.store.240101.2.msix",
                "win64-aarch64.msix": "target.store.240101.3.msix",
            },
        ),
        (
            {
                "release_rollout_percentage": 10,
            },
            "release",
            {},
            [],
            None,
            {
                "allowTargetFutureDeviceFamilies": {
                    "Desktop": True,
                    "Holographic": False,
                    "Mobile": False,
                    "Xbox": False,
                },
                "listings": {
                    "en-us": {
                        "baseListing": {
                            "copyrightAndTrademarkInfo": "",
                            "description": "Description",
                            "features": [],
                            "images": [],
                            "keywords": [],
                            "licenseTerms": "",
                            "privacyPolicy": "",
                            "recommendedHardware": [],
                            "releaseNotes": "",
                            "supportContact": "",
                            "title": "Firefox Nightly",
                            "websiteUrl": "",
                        },
                    },
                },
                "packageDeliveryOptions": {
                    "packageRollout": {
                        "isPackageRollout": True,
                        "packageRolloutPercentage": 10,
                    }
                },
            },
            {},
        ),
    ),
)
def test_craft_new_submission_request_and_upload_file_names(
    monkeypatch, config, channel, submission_request, file_paths, publish_mode, expected_submission_request, expected_upload_file_names
):
    monkeypatch.setattr(microsoft_store.time, "strftime", lambda _: "240101")
    assert microsoft_store._craft_new_submission_request_and_upload_file_names(config, channel, submission_request, file_paths, publish_mode) == (
        expected_submission_request,
        expected_upload_file_names,
    )


@pytest.mark.parametrize(
    "submission_request, expected",
    (
        ({}, b"{}"),
        (
            {
                "listings": {
                    "id": {
                        "baseListing": {
                            "description": "AMAN.\xa0\nPeramban",  # Bug 1909434
                        }
                    }
                }
            },
            b'{"listings": {"id": {"baseListing": {"description": "AMAN.\\u00a0\\nPeramban"}}}}',
        ),
    ),
)
def test_encode_submission_request(submission_request, expected):
    assert microsoft_store._encode_submission_request(submission_request, "utf-8") == expected


@pytest.mark.parametrize(
    "status_code, raises",
    (
        (200, False),
        (404, True),
        (503, True),
    ),
)
def test_commit_submission(status_code, raises):
    headers = {}
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    submission_id = 888
    mocked_response = {"status": "OK"}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}/commit")
            m.post(url, headers=headers, json=mocked_response, status_code=status_code)
            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._commit_submission(CONFIG, channel, session, submission_id, headers)
            else:
                microsoft_store._commit_submission(CONFIG, channel, session, submission_id, headers)


@pytest.mark.parametrize(
    "status_code, raises, mocked_response, exc",
    (
        (200, False, {"status": "CommitStarted"}, None),
        (200, False, {"status": "PreProcessing"}, None),
        (200, False, {"status": "PendingCommit"}, None),
        (200, True, {"status": "CommitFailed"}, TaskError),
        (404, True, {}, requests.exceptions.HTTPError),
        (503, True, {}, requests.exceptions.HTTPError),
    ),
)
def test_get_submission_status(status_code, raises, mocked_response, exc):
    headers = {}
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    submission_id = 888
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}/status")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            if raises:
                if exc != TaskError:
                    with pytest.raises(exc):
                        status = microsoft_store._get_submission_status(CONFIG, channel, session, submission_id, headers)
                with pytest.raises(exc):
                    microsoft_store._wait_for_commit_completion(CONFIG, channel, session, submission_id, headers)
            else:
                status = microsoft_store._get_submission_status(CONFIG, channel, session, submission_id, headers)
                assert status == mocked_response
                if mocked_response.get("status") in ("PreProcessing", "CommitFailed"):
                    status = microsoft_store._wait_for_commit_completion(CONFIG, channel, session, submission_id, headers)
                    assert status


@pytest.mark.parametrize(
    "submission_response, raises, exc",
    (
        ({"status": "PreProcessing"}, False, None),
        # Max polling attempts
        ({"status": "CommitStarted"}, True, TimeoutError),
        ({"status": "PendingCommit"}, True, TimeoutError),
        # Failed
        ({"status": "CommitFailed"}, True, TaskError),
    ),
)
def test_wait_for_commit_completion(monkeypatch, submission_response, raises, exc):
    monkeypatch.setattr(microsoft_store, "_get_submission_status", lambda *x: submission_response)
    # Make sure we don't wait between attempts
    monkeypatch.setattr(microsoft_store, "COMMIT_POLL_WAIT_SECONDS", 0)
    if raises:
        with pytest.raises(exc):
            microsoft_store._wait_for_commit_completion({}, "channel", {}, "id", {})
    else:
        microsoft_store._wait_for_commit_completion({}, "channel", {}, "id", {})


@pytest.mark.parametrize(
    "status_code, raises, mocked_response",
    (
        (200, False, {"status": "PreProcessing"}),
        (404, True, {}),
        (503, True, {}),
    ),
)
def test_push_to_store(status_code, raises, mocked_response):
    headers = {}
    access_token = "mock-token"
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    submission_id = 888
    upload_url = "https://some/url"
    publish_mode = "Manual"
    create_mocked_response = {"id": 888, "fileUploadUrl": "https://some/url", "applicationPackages": [{"minimumDirectXVersion": 1, "minimumSystemRam": 1024}]}
    with tempfile.NamedTemporaryFile(mode="wb") as f:
        f.write(b"hello there")
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(CONFIG, f"{application_id}")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}")
            m.delete(url, headers=headers)
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions")
            m.post(url, headers=headers, json=create_mocked_response, status_code=status_code)
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}")
            m.put(url, headers=headers, json=mocked_response, status_code=status_code)
            m.put(upload_url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}/commit")
            m.post(url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}/status")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)

            with patch.object(microsoft_store, "BlobClient"):
                if raises:
                    with pytest.raises(requests.exceptions.HTTPError):
                        microsoft_store._push_to_store(CONFIG, channel, [f.name], publish_mode, access_token)
                else:
                    microsoft_store._push_to_store(CONFIG, channel, [f.name], publish_mode, access_token)
