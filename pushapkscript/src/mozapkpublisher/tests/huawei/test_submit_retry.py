from unittest import mock

import pytest

import mozapkpublisher.huawei_api
from mozapkpublisher.huawei_api import (
    RELEASE_TYPE_FULL_ROLLOUT,
    SUBMIT_MINIMUM_RETRY_DELAY,
    SUBMIT_RETRY_DELAY,
    SUBMIT_RETRY_TIMEOUT,
    HuaweiAppGallery,
    _is_package_still_processing,
)
from mozapkpublisher.huawei_api.error import HuaweiException, HuaweiUpdateException
from mozapkpublisher.huawei_api.result_codes import PERMANENT_SUBMIT_SUB_CODES, SUBMIT_QUERY_FAILED
from .common import recorded_calls

CREDENTIALS = {"key_id": "k", "sub_account": "s", "private_key": "x"}
APP_SUBMIT_URL = "https://connect-api.cloud.huawei.com/api/publish/v2/app-submit?appId=appid-1&releaseType=1"

# The message Huawei really returns while a package is being parsed.
STILL_PROCESSING = {
    "ret": {
        "code": 204144660,
        "msg": "[cds]submit failed, additional msg is [The pkg: [firefox.apk] is being processed. "
               "It may take 2-5 minutes, depending on the size of the software package.]",
    }
}
COMPILING = {"ret": {"code": 204144727, "msg": "The package is being compiled. Please try again 3 to 5 minutes later."}}
SUCCESS = {"ret": {"code": 0, "msg": "ok"}}


@pytest.fixture
def no_retry_delay():
    """Keep the retry logic intact but make the waits instant."""
    with mock.patch.object(mozapkpublisher.huawei_api, "SUBMIT_RETRY_DELAY", 0):
        yield


@pytest.mark.parametrize(
    "ret,expected",
    (
        pytest.param(STILL_PROCESSING["ret"], True, id="apk_being_parsed"),
        pytest.param(COMPILING["ret"], True, id="package_compiling"),
        pytest.param({"code": 204144660, "msg": "包正在解析中"}, True, id="chinese_wording"),
        pytest.param({"code": 204144660, "msg": "registeredEntity can not be empty"}, False, id="permanent_reuse_of_the_code"),
        pytest.param({"code": 204144660, "msg": "80210099"}, False, id="permanent_compile_failure"),
        pytest.param(
            {"code": 204144660, "msg": "Failed to parse the AAB package using the bundletool."},
            False,
            id="permanent_parse_failure",
        ),
        pytest.param({"code": 204144660, "msg": "使用bundletool解析AAB包失败"}, False, id="permanent_parse_failure_chinese"),
        pytest.param(
            {"code": 204144660, "msg": "submit failed, msg is [registeredIdType and registeredIdNumber are required]"},
            False,
            id="missing_publisher_entity",
        ),
        pytest.param({"code": 204144660}, False, id="no_message"),
        pytest.param({"code": 204144661, "msg": "is being processed"}, False, id="unrelated_code"),
        pytest.param({"code": 0, "msg": "ok"}, False, id="success"),
    ),
)
def test_is_package_still_processing(ret, expected):
    assert _is_package_still_processing(ret) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("first_response", (STILL_PROCESSING, COMPILING), ids=["parsing", "compiling"])
async def test_submit_retries_while_the_package_is_processed(responses_mock, mock_jwt, no_retry_delay, first_response):
    """AppGallery parses packages asynchronously, so the first `app-submit` routinely
    fails with an HTTP 200 telling us to come back. That is not a release failure."""
    responses_mock.post(APP_SUBMIT_URL, payload=first_response)
    responses_mock.post(APP_SUBMIT_URL, payload=first_response)
    responses_mock.post(APP_SUBMIT_URL, payload=SUCCESS)

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        assert await huawei.submit_app("appid-1", RELEASE_TYPE_FULL_ROLLOUT) == SUCCESS

    assert len(recorded_calls(responses_mock, "POST", APP_SUBMIT_URL)) == 3


@pytest.mark.asyncio
async def test_submit_does_not_retry_a_terminal_failure(responses_mock, mock_jwt, no_retry_delay):
    """204144660 is reused for permanent failures. Retrying on the code alone would hide a
    real error behind a ten minute wait."""
    responses_mock.post(APP_SUBMIT_URL, payload={"ret": {"code": 204144660, "msg": "registeredEntity can not be empty"}})

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        with pytest.raises(HuaweiException, match="registeredEntity can not be empty"):
            await huawei.submit_app("appid-1", RELEASE_TYPE_FULL_ROLLOUT)

    assert len(recorded_calls(responses_mock, "POST", APP_SUBMIT_URL)) == 1


@pytest.mark.asyncio
async def test_submit_succeeds_on_the_first_attempt_without_waiting(responses_mock, mock_jwt):
    """A package that is already parsed must submit immediately -- no fixed sleep."""
    responses_mock.post(APP_SUBMIT_URL, payload=SUCCESS)

    with mock.patch.object(mozapkpublisher.huawei_api.asyncio, "sleep") as sleep_mock:
        async with HuaweiAppGallery(CREDENTIALS) as huawei:
            await huawei.submit_app("appid-1", RELEASE_TYPE_FULL_ROLLOUT)

    sleep_mock.assert_not_called()
    assert len(recorded_calls(responses_mock, "POST", APP_SUBMIT_URL)) == 1


@pytest.mark.asyncio
async def test_submit_gives_up_after_the_timeout(responses_mock, mock_jwt, no_retry_delay):
    responses_mock.post(APP_SUBMIT_URL, payload=STILL_PROCESSING, repeat=True)

    with mock.patch.object(mozapkpublisher.huawei_api, "SUBMIT_RETRY_TIMEOUT", -1):
        async with HuaweiAppGallery(CREDENTIALS) as huawei:
            with pytest.raises(HuaweiUpdateException) as exc:
                await huawei.submit_app("appid-1", RELEASE_TYPE_FULL_ROLLOUT)

    # The binary is already uploaded at this point, so the message has to say so.
    assert "AppGallery Connect console" in str(exc.value)
    assert "204144660" in str(exc.value)
    assert len(recorded_calls(responses_mock, "POST", APP_SUBMIT_URL)) == 1


def test_submit_retry_budget_covers_huaweis_documented_delay():
    """Huawei's own 204144727 message asks for a retry 3 to 5 minutes later, so the
    budget has to comfortably exceed that."""
    assert SUBMIT_RETRY_TIMEOUT >= 300


def test_submit_retry_delay_respects_the_minimum_call_interval():
    """Consecutive `app-submit` calls less than two minutes apart are rejected for the
    interval alone, so tuning the delay below that would make every retry fail for a
    reason that has nothing to do with the package.

    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-Guides/agcapi-pub-releasenotes-0000001111685226
    """
    assert SUBMIT_MINIMUM_RETRY_DELAY == 120
    assert SUBMIT_RETRY_DELAY >= SUBMIT_MINIMUM_RETRY_DELAY
    # At least a couple of retries have to fit inside the budget.
    assert SUBMIT_RETRY_TIMEOUT >= SUBMIT_RETRY_DELAY * 2


@pytest.mark.parametrize("sub_code", PERMANENT_SUBMIT_SUB_CODES)
def test_a_documented_sub_code_vetoes_a_retry(sub_code):
    """Every sub-code 204144660 embeds is permanent, so it must win even when the rest of
    the message reads like a package that is merely still being parsed."""
    ret = {
        "code": SUBMIT_QUERY_FAILED,
        "msg": "[cds]submit failed, additional msg is [{}: the pkg is being processed. "
               "It may take 2-5 minutes.]".format(sub_code),
    }
    assert _is_package_still_processing(ret) is False


def test_unrecognised_submit_failures_are_treated_as_permanent():
    """An unknown failure must surface at once rather than stall for the whole timeout."""
    assert _is_package_still_processing({"code": SUBMIT_QUERY_FAILED, "msg": "something new"}) is False
