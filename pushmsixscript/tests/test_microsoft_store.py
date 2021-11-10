import tempfile

import pytest
import requests
import requests_mock

from pushmsixscript import microsoft_store


@pytest.mark.parametrize(
    "status_code, raises",
    (
        (200, False),
        (404, True),
        (503, True),
    ),
)
def test_store_session(status_code, raises):
    tenant_id = "mock-tenant-id"
    client_id = "mock-client-id"
    client_secret = "mock-client-secret"
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
    expected_access_token = "mock-access-token"
    mocked_response = {"access_token": expected_access_token}

    with requests_mock.Mocker() as m:
        url = "https://login.microsoftonline.com/{0}/oauth2/token".format(tenant_id)
        m.post(url, headers=headers, json=mocked_response, status_code=status_code)
        if raises:
            with pytest.raises(requests.exceptions.HTTPError):
                token = microsoft_store._store_session(tenant_id, client_id, client_secret)
        else:
            token = microsoft_store._store_session(tenant_id, client_id, client_secret)
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
    application_id = 42
    submission_to_remove = 43
    if pending:
        mocked_response = {"pendingApplicationSubmission": {"id": submission_to_remove}}
    else:
        mocked_response = {}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(f"{application_id}")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(f"{application_id}/submissions/{submission_to_remove}")
            m.delete(url, headers=headers)

            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._remove_pending_submission(session, application_id, headers)
            else:
                microsoft_store._remove_pending_submission(session, application_id, headers)


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
    application_id = 42
    mocked_response = {"id": 888, "upload_url": "https://some/url"}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(f"{application_id}/submissions")
            m.post(url, headers=headers, json=mocked_response, status_code=status_code)
            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    (submission_id, upload_url) = microsoft_store._create_submission(session, application_id, headers)
            else:
                (submission_id, upload_url) = microsoft_store._create_submission(session, application_id, headers)
                assert submission_id == mocked_response["id"]
                assert upload_url == mocked_response["upload_url"]


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
    application_id = 42
    submission_id = 888
    upload_url = "https://some/url"
    app_submission_request = {}
    mocked_response = {"status": "OK"}
    with tempfile.NamedTemporaryFile(mode="wb") as f:
        f.write(b"hello there")
        with requests.Session() as session:
            with requests_mock.Mocker() as m:
                url = microsoft_store._store_url(f"{application_id}/submissions/{submission_id}")
                m.put(url, headers=headers, json=mocked_response, status_code=status_code)
                m.put(upload_url, headers=headers, json=mocked_response, status_code=upload_status_code)
                if raises:
                    with pytest.raises(requests.exceptions.HTTPError):
                        microsoft_store._update_submission(session, application_id, submission_id, headers, app_submission_request, f.name, upload_url)
                else:
                    microsoft_store._update_submission(session, application_id, submission_id, headers, app_submission_request, f.name, upload_url)
                    # XXX verify content of file_path uploaded?
                    # XXX verify submission_request?


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
    application_id = 42
    submission_id = 888
    mocked_response = {"status": "OK"}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(f"{application_id}/submissions/{submission_id}/commit")
            m.post(url, headers=headers, json=mocked_response, status_code=status_code)
            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._commit_submission(session, application_id, submission_id, headers)
            else:
                microsoft_store._commit_submission(session, application_id, submission_id, headers)


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
    application_id = 42
    submission_id = 888
    mocked_response = {"id": 888, "upload_url": "https://some/url"}
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._store_url(f"{application_id}/submissions/{submission_id}/status")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    status = microsoft_store._get_submission_status(session, application_id, submission_id, headers)
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._wait_for_commit_completion(session, application_id, submission_id, headers)
            else:
                status = microsoft_store._get_submission_status(session, application_id, submission_id, headers)
                assert status == mocked_response
                if mocked_response.get("status") != "CommitStarted":
                    status = microsoft_store._wait_for_commit_completion(session, application_id, submission_id, headers)
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
    application_id = 42
    submission_id = 888
    submission_request = {}
    upload_url = "https://some/url"
    create_mocked_response = {"id": 888, "upload_url": "https://some/url"}
    with tempfile.NamedTemporaryFile(mode="wb") as f:
        f.write(b"hello there")
        with requests_mock.Mocker() as m:

            url = microsoft_store._store_url(f"{application_id}")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(f"{application_id}/submissions/{submission_id}")
            m.delete(url, headers=headers)
            url = microsoft_store._store_url(f"{application_id}/submissions")
            m.post(url, headers=headers, json=create_mocked_response, status_code=status_code)
            url = microsoft_store._store_url(f"{application_id}/submissions/{submission_id}")
            m.put(url, headers=headers, json=mocked_response, status_code=status_code)
            m.put(upload_url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(f"{application_id}/submissions/{submission_id}/commit")
            m.post(url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._store_url(f"{application_id}/submissions/{submission_id}/status")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)

            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._push_to_store(f.name, access_token, application_id, submission_request)
            else:
                microsoft_store._push_to_store(f.name, access_token, application_id, submission_request)
