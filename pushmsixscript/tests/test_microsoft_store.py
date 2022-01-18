import tempfile

import pytest
import requests
import requests_mock

from pushmsixscript import microsoft_store

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
    "status_code, pending, raises",
    (
        (200, True, False),
        (200, False, False),
        (404, False, True),
        (503, False, True),
    ),
)
def test_remove_pending_submission(status_code, pending, raises):
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
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._remove_pending_submission(CONFIG, channel, session, headers)
            else:
                microsoft_store._remove_pending_submission(CONFIG, channel, session, headers)


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
                    submission_request = microsoft_store._create_submission(CONFIG, channel, session, headers)
            else:
                submission_request = microsoft_store._create_submission(CONFIG, channel, session, headers)
                assert submission_request == mocked_response


@pytest.mark.parametrize(
    "status_code, upload_status_code, raises",
    (
        (200, 200, False),
        (200, 404, True),
        (404, 200, True),
        (404, 405, True),
        (503, 504, True),
    ),
)
def test_update_submission(status_code, upload_status_code, raises):
    headers = {}
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    submission_request = {"id": 888, "fileUploadUrl": "https://some/url"}
    submission_id = submission_request["id"]
    upload_url = submission_request["fileUploadUrl"]
    mocked_response = {"status": "OK"}
    with tempfile.NamedTemporaryFile(mode="wb") as f:
        f.write(b"hello there")
        with requests.Session() as session:
            with requests_mock.Mocker() as m:
                url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}")
                m.put(url, headers=headers, json=mocked_response, status_code=status_code)
                m.put(upload_url, headers=headers, json=mocked_response, status_code=upload_status_code)
                if raises:
                    with pytest.raises(requests.exceptions.HTTPError):
                        microsoft_store._update_submission(CONFIG, channel, session, submission_request, headers, [f.name])
                else:
                    microsoft_store._update_submission(CONFIG, channel, session, submission_request, headers, [f.name])


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
    "status_code, raises, mocked_response",
    (
        (200, False, {"status": "CommitStarted"}),
        (200, False, {"status": "Done"}),
        (404, True, {}),
        (503, True, {}),
    ),
)
def test_get_submission_status(status_code, raises, mocked_response):
    headers = {}
    channel = "mock"
    application_id = CONFIG["application_ids"][channel]
    submission_id = 888
    mocked_response = {"id": 888, "fileUploadUrl": "https://some/url"}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(CONFIG, f"{application_id}/submissions/{submission_id}/status")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    status = microsoft_store._get_submission_status(CONFIG, channel, session, submission_id, headers)
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._wait_for_commit_completion(CONFIG, channel, session, submission_id, headers)
            else:
                status = microsoft_store._get_submission_status(CONFIG, channel, session, submission_id, headers)
                assert status == mocked_response
                if mocked_response.get("status") != "CommitStarted":
                    status = microsoft_store._wait_for_commit_completion(CONFIG, channel, session, submission_id, headers)
                    assert status


@pytest.mark.parametrize(
    "status_code, raises, mocked_response",
    (
        (200, False, {"status": "Done"}),
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
    create_mocked_response = {"id": 888, "fileUploadUrl": "https://some/url"}
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

            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._push_to_store(CONFIG, channel, [f.name], access_token)
            else:
                microsoft_store._push_to_store(CONFIG, channel, [f.name], access_token)
