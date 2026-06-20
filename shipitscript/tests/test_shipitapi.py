import json

import mock
import pytest
import redo
import requests

from shipitscript.shipitapi import Release_V2

# mock redo library, to make test faster
real_retry = redo.retry


def fake(*args, **kwargs):
    kwargs.pop("sleeptime")
    kwargs.pop("max_sleeptime")
    return real_retry(sleeptime=1, max_sleeptime=1, jitter=1, *args, **kwargs)


redo.retry = fake


def test_release_v2_class(mocker):
    class MockResponse(requests.Response):
        content = json.dumps({"success": True, "test": True})

        def __init__(self):
            super(MockResponse, self).__init__()
            self.status_code = 200

    # create release class
    release = Release_V2(taskcluster_client_id="some-id", taskcluster_access_token="some-token", api_root="https://www.apiroot.com/", retry_attempts=1)
    # mock requests library
    mocker.patch.object(release, "session")
    release_name = "releaseName"
    release.session.request.return_value = MockResponse()
    api_call_count = 0

    # test that getRelease call correct URL
    ret = release.getRelease(release_name)
    assert ret["test"] is True
    correct_url = "https://www.apiroot.com/releases/releaseName"
    release.session.request.assert_called_with(data=None, headers={}, method="GET", timeout=mock.ANY, verify=mock.ANY, url=correct_url)
    assert release.session.request.call_count == api_call_count + 1
    api_call_count += 1

    # test that getRelease pass the headers
    ret = release.getRelease(release_name, headers={"X-Test": "yes"})
    assert ret["test"] is True
    correct_url = "https://www.apiroot.com/releases/releaseName"
    release.session.request.assert_called_with(data=None, headers={"X-Test": "yes"}, method="GET", timeout=mock.ANY, verify=mock.ANY, url=correct_url)
    assert release.session.request.call_count == api_call_count + 1
    api_call_count += 1

    # test that update call correct URL
    headers = {"X-Test": "yes"}
    ret = release.update_status(release_name, status="success test", headers=headers)
    ret_json = json.loads(ret)
    assert ret_json["test"] is True
    correct_url = "https://www.apiroot.com/releases/releaseName"
    release.session.request.assert_called_with(
        data=json.dumps({"status": "success test"}), headers=mock.ANY, method="PATCH", timeout=mock.ANY, verify=mock.ANY, url=correct_url
    )
    api_call_count += 1
    assert release.session.request.call_count == api_call_count
    # make sure we don't modify the passed headers dictionary in the methods
    assert headers == {"X-Test": "yes"}

    # test that complete_merge_automation calls the right URL
    headers = {"X-Test": "yes"}
    ret = release.complete_merge_automation(123, headers=headers)
    ret_json = json.loads(ret)
    assert ret_json["test"] is True
    correct_url = "https://www.apiroot.com/merge-automation/123"
    release.session.request.assert_called_with(data="", headers=mock.ANY, method="PATCH", timeout=mock.ANY, verify=mock.ANY, url=correct_url)
    api_call_count += 1
    assert release.session.request.call_count == api_call_count
    assert headers == {"X-Test": "yes"}

    # test that exception raised if error, and retry api call
    release.session.request.return_value.status_code = 400
    with pytest.raises(requests.exceptions.HTTPError):
        release.getRelease(release_name)
    correct_url = "https://www.apiroot.com/releases/releaseName"
    release.session.request.assert_called_with(data=None, headers={}, method="GET", timeout=mock.ANY, verify=mock.ANY, url=correct_url)
    assert release.session.request.call_count == api_call_count + release.retries

    release.session.request.return_value.status_code = 200
    release.session.request.return_value.content = "Not JSON at all"
    with pytest.raises(json.decoder.JSONDecodeError):
        release.getRelease(release_name)


def test_release_v2_nightly_release(mocker):
    class MockResponse(requests.Response):
        _payload = {"success": True, "test": True}

        def __init__(self):
            super(MockResponse, self).__init__()
            self.status_code = 200

        def json(self):
            return self._payload

    release = Release_V2(taskcluster_client_id="some-id", taskcluster_access_token="some-token", api_root="https://www.apiroot.com/", retry_attempts=1)
    mocker.patch.object(release, "session")
    release.session.request.return_value = MockResponse()
    api_call_count = 0

    # test that get_nightly_metadata calls correct URL with query string
    headers = {"X-Test": "yes"}
    ret = release.get_nightly_metadata("firefox", "nightly", "20260525000000", headers=headers)
    assert ret["test"] is True
    correct_url = "https://www.apiroot.com/nightly-release?product=firefox&channel=nightly&buildid=20260525000000"
    release.session.request.assert_called_with(data=None, headers={"X-Test": "yes"}, method="GET", timeout=mock.ANY, verify=mock.ANY, url=correct_url)
    api_call_count += 1
    assert release.session.request.call_count == api_call_count
    # make sure we don't modify the passed headers dictionary in the methods
    assert headers == {"X-Test": "yes"}

    # test that get_nightly_metadata works with no headers
    ret = release.get_nightly_metadata("firefox", "nightly", "20260525000000")
    assert ret["test"] is True
    release.session.request.assert_called_with(data=None, headers={}, method="GET", timeout=mock.ANY, verify=mock.ANY, url=correct_url)
    api_call_count += 1
    assert release.session.request.call_count == api_call_count

    # test that create_new_nightly_release calls correct URL
    headers = {"X-Test": "yes"}
    ret = release.create_new_nightly_release("firefox", "nightly", "20260525000000", "150.0a1", ["en-US", "de"], headers=headers)
    assert ret["test"] is True
    correct_url = "https://www.apiroot.com/nightly-release"
    expected_data = json.dumps(
        {
            "product": "firefox",
            "channel": "nightly",
            "buildid": "20260525000000",
            "version": "150.0a1",
            "locales": ["en-US", "de"],
        }
    )
    release.session.request.assert_called_with(data=expected_data, headers=mock.ANY, method="POST", timeout=mock.ANY, verify=mock.ANY, url=correct_url)
    api_call_count += 1
    assert release.session.request.call_count == api_call_count
    assert headers == {"X-Test": "yes"}

    # test that exception is raised on error, and api call is retried
    release.session.request.return_value.status_code = 400
    with pytest.raises(requests.exceptions.HTTPError):
        release.get_nightly_metadata("firefox", "nightly", "20260525000000")
    assert release.session.request.call_count == api_call_count + release.retries
