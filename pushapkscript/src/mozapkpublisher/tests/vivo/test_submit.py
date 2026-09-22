import pytest

from .common import PUBLIC_PARAM_NAMES, ROUTER_URL, business_failure, posted_params, success
from .fixtures import ACCESS_SECRET
from mozapkpublisher.vivo_api import (
    METHOD_APP_DETAIL,
    METHOD_UPDATE_SUBMIT,
    ONLINE_TYPE_PUBLISH_NOW,
    ONLINE_TYPE_SCHEDULED,
)
from mozapkpublisher.vivo_api.auth import sign_params
from mozapkpublisher.vivo_api.error import VivoUpdateException

PACKAGE_NAME = "org.mozilla.firefox"


def test_the_online_type_values_are_the_ones_vivo_documents():
    """Every other assertion compares what was sent against these same constants, so
    only a literal catches them drifting from the documented wire values."""
    assert (ONLINE_TYPE_PUBLISH_NOW, ONLINE_TYPE_SCHEDULED) == (1, 2)


@pytest.mark.asyncio
async def test_update_submit_publishes_now_by_default(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=success())

    await vivo.update_submit(PACKAGE_NAME)

    params = posted_params(responses_mock)
    assert params["method"] == METHOD_UPDATE_SUBMIT
    assert params["packageName"] == PACKAGE_NAME
    assert params["onlineType"] == ONLINE_TYPE_PUBLISH_NOW
    # Publishing now takes no time, and the optional parameters are left out entirely
    # rather than sent as nulls.
    assert "onlineTime" not in params
    assert "remark" not in params


@pytest.mark.asyncio
async def test_update_submit_signs_its_parameters(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=success())

    await vivo.update_submit(PACKAGE_NAME)

    params = dict(posted_params(responses_mock))
    assert PUBLIC_PARAM_NAMES.issubset(params.keys())
    signature = params.pop("sign")
    assert signature == sign_params(params, ACCESS_SECRET)


@pytest.mark.asyncio
async def test_update_submit_can_schedule_a_publication(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=success())

    await vivo.update_submit(PACKAGE_NAME, ONLINE_TYPE_SCHEDULED, online_time=1599536920000, remark="a note")

    params = posted_params(responses_mock)
    assert params["onlineType"] == ONLINE_TYPE_SCHEDULED
    assert params["onlineTime"] == 1599536920000
    assert params["remark"] == "a note"


@pytest.mark.asyncio
async def test_a_scheduled_publication_needs_a_time(vivo, responses_mock):
    """vivo cannot infer the publication time, and omitting it fails server-side with
    A0310. Catching it here keeps the request from going out at all."""
    with pytest.raises(VivoUpdateException, match="requires `online_time`"):
        await vivo.update_submit(PACKAGE_NAME, ONLINE_TYPE_SCHEDULED)


@pytest.mark.asyncio
async def test_update_submit_surfaces_a_refusal(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=business_failure("A0305", "The app is under review"))

    with pytest.raises(VivoUpdateException, match="already under review"):
        await vivo.update_submit(PACKAGE_NAME)


@pytest.mark.asyncio
async def test_get_app_detail_returns_the_data_object(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=success({"packageName": PACKAGE_NAME, "status": 0, "versionCode": 100}))

    detail = await vivo.get_app_detail(PACKAGE_NAME)

    assert detail["versionCode"] == 100
    assert posted_params(responses_mock)["method"] == METHOD_APP_DETAIL


@pytest.mark.asyncio
async def test_get_app_detail_without_data(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=success(None))

    assert await vivo.get_app_detail(PACKAGE_NAME) == {}


def test_the_production_gateway_is_not_left_pointing_at_a_test_route():
    """Guards against committing the scratch values used when driving the client against
    a local server by hand. The rest of this package derives its URL from these constants,
    so this is the one place that pins them to what the vivo documentation specifies."""
    from mozapkpublisher import vivo_api

    assert vivo_api.BASE_URL == "https://developer-api.vivo.com/"
    assert vivo_api.ROUTER_ROUTE == "/router/rest"
