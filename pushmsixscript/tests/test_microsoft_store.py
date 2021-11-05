import os

import pytest
import requests
import requests_mock
from scriptworker.exceptions import TaskVerificationError

from pushmsixscript import microsoft_store

# from pushmsixscript.exceptions import AlreadyLatestError


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
    url = "https://login.microsoftonline.com/{0}/oauth2/token".format(tenant_id)

    with requests_mock.Mocker() as m:
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
            url = microsoft_store._format_url(f"{application_id}")
            m.get(url, headers=headers, json=mocked_response, status_code=status_code)
            url = microsoft_store._format_url(f"{application_id}/submissions/{submission_to_remove}")
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
            url = microsoft_store._format_url(f"{application_id}/submissions")
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
    # XXX tempfile?
    file_path = "tmp.tmp"
    with open(file_path, "wb") as f:
        f.write(b"hello there")
    with requests.Session() as session:
        with requests_mock.Mocker() as m:
            url = microsoft_store._format_url(f"{application_id}/submissions/{submission_id}")
            m.put(url, headers=headers, json=mocked_response, status_code=status_code)
            m.put(upload_url, headers=headers, json=mocked_response, status_code=upload_status_code)
            if raises:
                with pytest.raises(requests.exceptions.HTTPError):
                    microsoft_store._update_submission(session, application_id, submission_id, headers, app_submission_request, file_path, upload_url)
            else:
                microsoft_store._update_submission(session, application_id, submission_id, headers, app_submission_request, file_path, upload_url)
                # XXX verify content of file_path uploaded?
                # XXX verify submission_request?
    os.remove(file_path)


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
            url = microsoft_store._format_url(f"{application_id}/submissions/{submission_id}/commit")
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
            url = microsoft_store._format_url(f"{application_id}/submissions/{submission_id}/status")
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
                    assert status == True


"""
@pytest.mark.parametrize(
    "channel, expected_macaroon_location, raises, exception_message, bubbles_up_exception",
    (
        ("beta", "/path/to/macaroon_beta", False, None, False),
        ("candidate", "/path/to/macaroon_candidate", False, None, False),
        ("candidate", "/path/to/macaroon_candidate", True, "some random message", True),
        ("candidate", "/path/to/macaroon_candidate", True, "A file with this exact same content has already been uploaded", False),
    ),
)
def test_push(monkeypatch, channel, expected_macaroon_location, raises, exception_message, bubbles_up_exception):
    fake_release_if_needed_count = (n for n in range(0, 2))

    context = MagicMock()
    context.config = {"push_to_store": True, "macaroons_locations": {"beta": "/path/to/macaroon_beta", "candidate": "/path/to/macaroon_candidate"}}
    store = MagicMock()
    store_client_mock = MagicMock()

    @contextlib.contextmanager
    def fake_store_session(macaroon_location):
        assert macaroon_location == expected_macaroon_location
        yield store

    monkeypatch.setattr(microsoft_store, "_store_session", fake_store_session)
    monkeypatch.setattr(microsoft_store, "snapcraft_store_client", store_client_mock)
    store_client_mock.push.side_effect = (
        microsoft_store.StoreReviewError({"errors": [{"message": exception_message}], "code": "processing_error"}) if raises else None
    )

    def fake_release_if_needed(store_, channel_, msix_file_path):
        assert store_ is store
        assert channel_ == channel_
        assert msix_file_path == "/path/to/file.store.msix"
        next(fake_release_if_needed_count)

    monkeypatch.setattr(microsoft_store, "_release_if_needed", fake_release_if_needed)

    if bubbles_up_exception:
        with pytest.raises(microsoft_store.StoreReviewError):
            microsoft_store.push(context, "/path/to/file.store.msix", channel)
        assert next(fake_release_if_needed_count) == 0
    else:
        microsoft_store.push(context, "/path/to/file.store.msix", channel)
        assert next(fake_release_if_needed_count) == 1


def test_push_early_return_if_not_allowed(monkeypatch):
    call_count = (n for n in range(0, 2))

    context = MagicMock()

    def increase_call_count(_, __):
        next(call_count)

    monkeypatch.setattr(microsoft_store.snapcraft_store_client, "push", increase_call_count)
    microsoft_store.push(context, "/some/file.store.msix", channel="mock")

    assert next(call_count) == 0


class SomeSpecificException(Exception):
    pass


@pytest.mark.parametrize("raises", (True, False))
def test_store_session(monkeypatch, raises):
    # monkeypatch.setattr(microsoft_store, "StoreClient", lambda: store_client_mock)
    tenant_id = "mock-tenant-id"
    client_id = "mock-client-id"
    client_secret = "mock-client-secret"

    if raises:
        with pytest.raises(SomeSpecificException):
            token = microsoft_store._store_session(tenant_id, client_id, client_secret)
            raise SomeSpecificException("Oh noes!")
    else:
        token = microsoft_store._store_session(tenant_id, client_id, client_secret)


@pytest.mark.parametrize(
    "channel, raises, exception, bubbles_up_exception, must_release, release_kwargs",
    (
        ("beta", True, TaskVerificationError, True, False, None),
        ("beta", True, AlreadyLatestError, False, False, None),
        ("beta", False, None, False, True, {"msix_name": "firefox", "revision": 3, "channels": ["beta"]}),
        ("stable", False, None, False, True, {"msix_name": "firefox", "revision": 3, "channels": ["stable"]}),
    ),
)
def test_release_if_needed(monkeypatch, channel, raises, exception, bubbles_up_exception, must_release, release_kwargs):
    store = MagicMock()

    def return_dummy(*args, **kwargs):
        return "dummy"

    def return_dummy_tuple(*args, **kwargs):
        return ("dummy", "tuple")

    monkeypatch.setattr(microsoft_store, "_list_all_revisions", return_dummy)
    monkeypatch.setattr(microsoft_store, "_pluck_metadata", return_dummy)
    monkeypatch.setattr(microsoft_store, "_filter_versions_that_are_not_the_same_type", return_dummy)
    monkeypatch.setattr(microsoft_store, "_populate_sha3_384", return_dummy)
    monkeypatch.setattr(microsoft_store, "get_hash", return_dummy)
    monkeypatch.setattr(microsoft_store, "_find_revision_and_version_of_current_msix", lambda _, __: (3, "version"))
    monkeypatch.setattr(microsoft_store, "_pick_revision_and_version_of_latest_released_msix", return_dummy_tuple)

    def check_current(*args):
        if raises:
            if exception == AlreadyLatestError:
                raise exception("version", "rev")
            else:
                raise exception("some message")

    monkeypatch.setattr(microsoft_store, "_check_current_msix_is_not_released", check_current)

    if bubbles_up_exception:
        with pytest.raises(exception):
            microsoft_store._release_if_needed(store, channel, "/path/to/file.store.msix")
    else:
        microsoft_store._release_if_needed(store, channel, "/path/to/file.store.msix")

    if must_release:
        store.release.assert_called_once_with(**release_kwargs)
    else:
        store.release.assert_not_called()


def test_list_all_revisions():
    store = MagicMock()
    store.get_msix_revisions.return_value = [
        {"revision": 1, "version": "63.0b1-1", "current_channels": [], "some_other": "field"},
        {"revision": 2, "version": "63.0b2-1", "current_channels": []},
    ]

    assert microsoft_store._list_all_revisions(store) == [
        {"revision": 1, "version": "63.0b1-1", "current_channels": [], "some_other": "field"},
        {"revision": 2, "version": "63.0b2-1", "current_channels": []},
    ]
    store.get_msix_revisions.assert_called_once_with("firefox")


def test_pluck_metadata():
    assert microsoft_store._pluck_metadata(
        [
            {"revision": 1, "version": "63.0b1-1", "current_channels": [], "some_other": "field"},
            {"revision": 2, "version": "63.0b2-1", "current_channels": []},
            {"revision": 3, "version": "62.0-1", "current_channels": ["release", "candidate"]},
            {"revision": 4, "version": "63.0b3-1", "current_channels": ["beta", "edge"]},
            {"revision": 5, "version": "60.2.1esr-1", "current_channels": ["esr/stable", "esr/candidate", "esr/beta", "esr/edge"]},
        ]
    ) == {
        1: {"version": GeckoSnapVersion.parse("63.0b1-1"), "current_channels": []},
        2: {"version": GeckoSnapVersion.parse("63.0b2-1"), "current_channels": []},
        3: {"version": GeckoSnapVersion.parse("62.0-1"), "current_channels": ["release", "candidate"]},
        4: {"version": GeckoSnapVersion.parse("63.0b3-1"), "current_channels": ["beta", "edge"]},
        5: {"version": GeckoSnapVersion.parse("60.2.1esr-1"), "current_channels": ["esr/stable", "esr/candidate", "esr/beta", "esr/edge"]},
    }


@pytest.mark.parametrize(
    "channel, expected",
    (
        (
            "beta",
            {
                1: {"version": GeckoSnapVersion.parse("63.0b1-1")},
                2: {"version": GeckoSnapVersion.parse("63.0b2-1")},
                3: {"version": GeckoSnapVersion.parse("62.0-1")},
                4: {"version": GeckoSnapVersion.parse("63.0b3-1")},
            },
        ),
        ("stable", {3: {"version": GeckoSnapVersion.parse("62.0-1")}}),
        ("esr/stable", {5: {"version": GeckoSnapVersion.parse("60.2.1esr-1")}}),
        ("esr/candidate", {5: {"version": GeckoSnapVersion.parse("60.2.1esr-1")}}),
    ),
)
def test_filter_versions_that_are_not_the_same_type(channel, expected):
    assert (
        microsoft_store._filter_versions_that_are_not_the_same_type(
            {
                1: {"version": GeckoSnapVersion.parse("63.0b1-1")},
                2: {"version": GeckoSnapVersion.parse("63.0b2-1")},
                3: {"version": GeckoSnapVersion.parse("62.0-1")},
                4: {"version": GeckoSnapVersion.parse("63.0b3-1")},
                5: {"version": GeckoSnapVersion.parse("60.2.1esr-1")},
            },
            channel,
        )
        == expected
    )


def test_populate_sha3_384(monkeypatch):
    metadata_per_revision = {
        1: {"version": "63.0b1-1", "current_channels": []},
        2: {"version": "63.0b2-1", "current_channels": ["beta"]},
        3: {"version": "63.0b3-1", "current_channels": ["beta"]},
    }

    def gen_fake_hash(_, revision):
        return "fake_hash_rev{}".format(revision)

    store = MagicMock()

    monkeypatch.setattr(microsoft_store, "_get_from_sha3_384_from_revision", gen_fake_hash)

    assert microsoft_store._populate_sha3_384(store, metadata_per_revision) == {
        2: {"version": "63.0b2-1", "current_channels": ["beta"], "download_sha3_384": "fake_hash_rev2"},
        3: {"version": "63.0b3-1", "current_channels": ["beta"], "download_sha3_384": "fake_hash_rev3"},
    }


def test_get_from_sha3_384_from_revision():
    store = MagicMock()
    store.cpi.get_default_headers.return_value = {"some_default": "header"}
    store_get_mock = MagicMock()
    store_get_mock.json.return_value = {"download_sha3_384": "some_sha3_384"}
    store.cpi.get.return_value = store_get_mock

    assert microsoft_store._get_from_sha3_384_from_revision(store, 2) == "some_sha3_384"
    store.cpi.get.assert_called_once_with(
        "api/v1/snaps/details/firefox",
        headers={"some_default": "header", "Accept": "application/hal+json", "X-Ubuntu-Series": "16"},
        params={"fields": "status,download_sha3_384,revision", "revision": 2},
    )


@pytest.mark.parametrize(
    "metadata_per_revision, raises, expected",
    (
        (
            {
                2: {"version": "63.0b6-1", "download_sha3_384": "a_hash"},
                3: {"version": "63.0b6-2", "download_sha3_384": "some_sha3_384"},
                4: {"version": "63.0b7-1", "download_sha3_384": "another_hash"},
            },
            False,
            (3, "63.0b6-2"),
        ),
        ({2: {"version": "63.0b6-1", "download_sha3_384": "a_hash"}}, True, ValueError),
        (
            {3: {"version": "63.0b6-2", "download_sha3_384": "some_sha3_384"}, 4: {"version": "63.0b7-1", "download_sha3_384": "some_sha3_384"}},
            True,
            ValueError,
        ),
    ),
)
def test_find_revision_and_version_of_current_msix(metadata_per_revision, raises, expected):
    if raises:
        with pytest.raises(expected):
            microsoft_store._find_revision_and_version_of_current_msix(metadata_per_revision, "some_sha3_384")
    else:
        microsoft_store._find_revision_and_version_of_current_msix(metadata_per_revision, "some_sha3_384")


@pytest.mark.parametrize(
    "current_revision, current_version, latest_released_revision, latest_released_version, raises, expected",
    (
        (131, GeckoSnapVersion.parse("63.0b8-1"), 130, GeckoSnapVersion.parse("63.0b7-1"), False, None),
        (131, GeckoSnapVersion.parse("63.0b8-1"), 131, GeckoSnapVersion.parse("63.0b8-1"), True, AlreadyLatestError),
        (133, GeckoSnapVersion.parse("62.0.2-1"), 131, GeckoSnapVersion.parse("63.0b8-1"), True, TaskVerificationError),
        (130, GeckoSnapVersion.parse("63.0b7-1"), 131, GeckoSnapVersion.parse("63.0b8-1"), True, TaskVerificationError),
        (132, GeckoSnapVersion.parse("63.0b8-1"), 131, GeckoSnapVersion.parse("63.0b8-1"), True, TaskVerificationError),
        (130, GeckoSnapVersion.parse("63.0b8-1"), 131, GeckoSnapVersion.parse("63.0b8-1"), True, TaskVerificationError),
    ),
)
def test_check_current_msix(current_revision, current_version, latest_released_version, latest_released_revision, raises, expected):
    if raises:
        with pytest.raises(expected):
            microsoft_store._check_current_msix_is_not_released(current_revision, current_version, latest_released_revision, latest_released_version)
    else:
        microsoft_store._check_current_msix_is_not_released(current_revision, current_version, latest_released_revision, latest_released_version)


@pytest.mark.parametrize(
    "channel, metadata_per_revision, raises, expected",
    (
        (
            "beta",
            {
                2: {"version": "63.0b6-1", "current_channels": []},
                3: {"version": "63.0b6-2", "current_channels": []},
                4: {"version": "63.0b7-1", "current_channels": ["beta", "edge"]},
            },
            False,
            (4, "63.0b7-1"),
        ),
        (
            "beta",
            {
                2: {"version": "63.0b6-1", "current_channels": []},
                3: {"version": "63.0b6-2", "current_channels": []},
                4: {"version": "63.0b7-1", "current_channels": ["beta", "edge"]},
                5: {"version": "63.0b7-2", "current_channels": []},
            },
            False,
            (4, "63.0b7-1"),
        ),
        (
            "beta",
            {
                2: {"version": "63.0b6-1", "current_channels": []},
                3: {"version": "63.0b6-2", "current_channels": []},
                4: {"version": "63.0b7-1", "current_channels": []},
            },
            True,
            ValueError,
        ),
        (
            "beta",
            {
                2: {"version": "63.0b6-1", "current_channels": []},
                3: {"version": "63.0b6-2", "current_channels": ["beta"]},
                4: {"version": "63.0b7-1", "current_channels": ["beta", "edge"]},
            },
            True,
            ValueError,
        ),
        (
            "esr/stable",
            {
                3: {"version": "63.0b6-2", "current_channels": []},
                4: {"version": "63.0b7-1", "current_channels": ["beta", "edge"]},
                5: {"version": "60.2.0esr", "current_channels": []},
                6: {"version": "60.2.1esr", "current_channels": ["esr/stable", "esr/candidate", "esr/beta", "esr/nightly"]},
            },
            False,
            (6, "60.2.1esr"),
        ),
        (
            "esr/stable",
            {
                3: {"version": "63.0b6-2", "current_channels": []},
                4: {"version": "63.0b7-1", "current_channels": ["beta", "edge"]},
                5: {"version": "60.2.0esr", "current_channels": []},
                6: {"version": "60.2.1esr", "current_channels": ["esr/stable"]},
                7: {"version": "67.0esr", "current_channels": ["esr/candidate", "esr/beta", "esr/nightly"]},
            },
            False,
            (6, "60.2.1esr"),
        ),
        (
            "esr/stable",
            {
                3: {"version": "63.0b6-2", "current_channels": []},
                4: {"version": "63.0b7-1", "current_channels": ["beta", "edge"]},
                5: {"version": "60.2.0esr", "current_channels": []},
                6: {"version": "60.2.1esr", "current_channels": ["esr/stable"]},
                7: {"version": "67.0esr", "current_channels": ["esr/candidate", "esr/beta", "esr/nightly"]},
            },
            False,
            (6, "60.2.1esr"),
        ),
        (
            "esr/candidate",
            {
                3: {"version": "63.0b6-2", "current_channels": []},
                4: {"version": "63.0b7-1", "current_channels": ["beta", "edge"]},
                5: {"version": "60.2.0esr", "current_channels": []},
                6: {"version": "60.2.1esr", "current_channels": ["esr/stable"]},
                7: {"version": "67.0esr", "current_channels": ["esr/candidate", "esr/beta", "esr/nightly"]},
            },
            False,
            (7, "67.0esr"),
        ),
    ),
)
def test_pick_revision_and_version_of_latest_released_msix(channel, metadata_per_revision, raises, expected):
    if raises:
        with pytest.raises(expected):
            microsoft_store._pick_revision_and_version_of_latest_released_msix(channel, metadata_per_revision)
    else:
        assert microsoft_store._pick_revision_and_version_of_latest_released_msix(channel, metadata_per_revision) == expected
"""
