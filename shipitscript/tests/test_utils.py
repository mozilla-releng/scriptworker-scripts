from unittest.mock import MagicMock

import pytest
from scriptworker.exceptions import ScriptWorkerTaskException

from shipitscript.utils import check_release_has_values_v2, get_auth_primitives_v2, get_request_headers, same_timing


@pytest.mark.parametrize(
    "ship_it_instance_config,expected",
    (
        (
            {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some-ship-it.url", "timeout_in_seconds": 1},
            ("some-id", "some-token", "http://some-ship-it.url", 1),
        ),
        (
            {"taskcluster_client_id": "some-id", "taskcluster_access_token": "some-token", "api_root_v2": "http://some-ship-it.url"},
            ("some-id", "some-token", "http://some-ship-it.url", 60),
        ),
    ),
)
def test_get_auth_primitives_v2(ship_it_instance_config, expected):
    assert get_auth_primitives_v2(ship_it_instance_config) == expected


@pytest.mark.parametrize(
    "release_info,  values, raises",
    (
        (
            {
                "name": "Fennec-X.0bX-build42",
                "shippedAt": "2018-07-03T09:19:00+00:00",
                "mh_changeset": "",
                "mozillaRelbranch": None,
                "version": "X.0bX",
                "branch": "projects/maple",
                "submitter": "shipit-scriptworker-stage",
                "ready": True,
                "mozillaRevision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "release_eta": None,
                "starter": None,
                "complete": True,
                "submittedAt": "2018-07-02T09:18:39+00:00",
                "status": "shipped",
                "comment": None,
                "product": "fennec",
                "description": None,
                "buildNumber": 42,
                "l10nChangesets": {},
            },
            {"status": "shipped"},
            False,
        ),
        (
            {
                "name": "Fennec-X.0bX-build42",
                "shippedAt": "2018-07-03T09:19:00+00:00",
                "mh_changeset": "",
                "mozillaRelbranch": None,
                "version": "X.0bX",
                "branch": "projects/maple",
                "submitter": "shipit-scriptworker-stage",
                "ready": True,
                "mozillaRevision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "release_eta": None,
                "starter": None,
                "complete": True,
                "submittedAt": "2018-07-02T09:18:39+00:00",
                "status": "Started",
                "comment": None,
                "product": "fennec",
                "description": None,
                "buildNumber": 42,
                "l10nChangesets": {},
            },
            {"status": "shipped"},
            True,
        ),
    ),
)
def test_generic_validation_v2(monkeypatch, release_info, values, raises):
    release_name = "Fennec-X.0bX-build42"
    ReleaseClassMock = MagicMock()
    attrs = {"getRelease.return_value": release_info}
    ReleaseClassMock.configure_mock(**attrs)

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_release_has_values_v2(ReleaseClassMock, release_name, {}, **values)
    else:
        check_release_has_values_v2(ReleaseClassMock, release_name, {}, **values)


@pytest.mark.parametrize(
    "time1,time2, expected",
    (
        ("2018-07-02 16:51:04", "2018-07-02T16:51:04+00:00", True),
        ("2018-07-02 16:51:04", "2018-07-02T16:51:04+01:00", False),
        ("2018-07-02 16:51:04", "2018-07-02T16:51:04+00:11", False),
        ("2018-07-02 16:51:04", "2018-07-02T16:51:04", True),
    ),
)
def test_same_timing(time1, time2, expected):
    assert same_timing(time1, time2) == expected


@pytest.mark.parametrize(
    "api_root, expected",
    (
        ("http://example.com", {"X-Forwarded-Proto": "https", "X-Forwarded-Port": "80"}),
        ("https://example.com", {"X-Forwarded-Proto": "https", "X-Forwarded-Port": "443"}),
        ("https://example.com:1234", {"X-Forwarded-Proto": "https", "X-Forwarded-Port": "1234"}),
    ),
)
def test_request_headers(api_root, expected):
    assert get_request_headers(api_root) == expected
