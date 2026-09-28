import os

import pytest

from .common import ROUTER_URL, app_detail, form_fields, recorded_calls, register_publish_flow, success, upload_success
from .fixtures import apk_metadata
from mozapkpublisher.common.store_api import build_apk_file_name
from mozapkpublisher.vivo_api import (
    METHOD_APP_DETAIL,
    METHOD_UPDATE_BASIC_INFO,
    METHOD_UPDATE_SUBMIT,
    METHOD_UPLOAD_APK,
    ONLINE_TYPE_PUBLISH_NOW,
    VivoAppStore,
)
from mozapkpublisher.vivo_api.error import VivoContentInfoException, VivoUpdateException

PACKAGE_NAME = "org.mozilla.firefox"
ACCESS_KEY = "k"
ACCESS_SECRET = "s"


def _methods_called(responses_mock):
    """The `method` parameter of each request, in order, so the flow can be asserted."""
    methods = []
    for call in recorded_calls(responses_mock):
        data = call.kwargs["data"]
        if isinstance(data, dict):
            methods.append(data["method"])
        else:
            methods.append(dict((t["name"], v) for t, _h, v in data._fields)["method"])
    return methods


@pytest.mark.asyncio
async def test_upload_apks_binds_the_upload_before_submitting(responses_mock, apk):
    """`app.update.submit` carries no APK reference, so without the `app.update.basic.info`
    bind in between it would submit whatever binary the app was already holding."""
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    assert _methods_called(responses_mock) == [
        METHOD_APP_DETAIL,
        METHOD_UPLOAD_APK,
        METHOD_UPDATE_BASIC_INFO,
        METHOD_UPDATE_SUBMIT,
    ]


@pytest.mark.asyncio
async def test_the_binary_is_uploaded_under_its_release_file_name(responses_mock, apk):
    """The store shows the uploaded file name, and reusing one across releases has failed
    an upload before (Bug 1974870), so it is derived from the APK metadata rather than
    being whatever the temp file on disk happened to be called."""
    fd, metadata = apk
    register_publish_flow(responses_mock, fd.name)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None)

    upload_call = recorded_calls(responses_mock)[1]
    file_name = form_fields(upload_call.kwargs["data"])["file"][0]
    assert file_name == build_apk_file_name(metadata)
    assert file_name != os.path.basename(fd.name)


@pytest.mark.asyncio
async def test_the_bind_carries_the_serial_number_from_the_upload(responses_mock, apk):
    """The serial number the upload returned is what gets bound - not a stale one, and
    not dropped on the floor."""
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    bind_call = recorded_calls(responses_mock)[2]
    assert bind_call.kwargs["data"]["apk"] == "serial-1"
    assert bind_call.kwargs["data"]["packageName"] == PACKAGE_NAME


@pytest.mark.asyncio
async def test_upload_apks_submits_for_immediate_publication(responses_mock, apk):
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    submit_call = recorded_calls(responses_mock)[3]
    assert submit_call.kwargs["data"]["onlineType"] == ONLINE_TYPE_PUBLISH_NOW


@pytest.mark.asyncio
async def test_upload_apks_without_submit_still_binds(responses_mock, apk):
    """Without `--submit` the release is staged rather than published - but it is only
    genuinely staged because the bind still happens. Uploading alone would leave nothing
    for a human to find in the console."""
    fd, _metadata_ = apk
    register_publish_flow(responses_mock, fd.name, submit=False)

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=False)

    assert _methods_called(responses_mock) == [METHOD_APP_DETAIL, METHOD_UPLOAD_APK, METHOD_UPDATE_BASIC_INFO]


@pytest.mark.asyncio
async def test_a_failed_bind_aborts_before_submitting(responses_mock, apk):
    """If the binary could not be bound, submitting would publish the previously bound
    one, so the flow has to stop here."""
    fd, _metadata_ = apk
    responses_mock.post(ROUTER_URL, payload=app_detail())
    responses_mock.post(ROUTER_URL, payload=upload_success(fd.name))
    responses_mock.post(ROUTER_URL, payload={"code": "0", "subCode": "A0109", "msg": "success", "subMsg": "The uploaded app file does not exist"})

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(Exception, match="does not exist"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    assert _methods_called(responses_mock) == [METHOD_APP_DETAIL, METHOD_UPLOAD_APK, METHOD_UPDATE_BASIC_INFO]


@pytest.mark.asyncio
async def test_a_failed_upload_aborts_before_submitting(responses_mock, apk):
    """An upload failure must stop the flow rather than let it carry on and submit
    whatever binary the app happened to be holding already."""
    responses_mock.post(ROUTER_URL, payload=app_detail())
    responses_mock.post(ROUTER_URL, payload={"code": "0", "subCode": "A0113", "msg": "success", "subMsg": "package name is not consistent"})

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(Exception, match="not consistent"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    assert _methods_called(responses_mock) == [METHOD_APP_DETAIL, METHOD_UPLOAD_APK]


@pytest.mark.asyncio
async def test_a_failed_upload_aborts_before_binding(responses_mock, apk):
    """Nothing may be bound if the upload did not land, or the app would keep pointing at
    the previous binary while the task reports progress."""
    responses_mock.post(ROUTER_URL, payload=app_detail())
    responses_mock.post(ROUTER_URL, payload=success({"packageName": PACKAGE_NAME, "serialNumber": ""}))

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(Exception, match="serial number"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    assert _methods_called(responses_mock) == [METHOD_APP_DETAIL, METHOD_UPLOAD_APK]


@pytest.mark.asyncio
async def test_a_rollout_is_refused(responses_mock, apk):
    """vivo publishes to everyone at once. Submitting anyway would turn a 10% rollout
    request into a release to 100% of users, so the task fails instead."""
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(VivoUpdateException) as exc:
            await vivo.upload_apks(PACKAGE_NAME, [apk], 10, submit=True)

    message = str(exc.value)
    assert "no staged rollout" in message
    assert "10%" in message
    assert recorded_calls(responses_mock) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("rollout_rate", (0, 100))
async def test_any_rollout_percentage_is_refused(responses_mock, apk, rollout_rate):
    """`--rollout-percentage` accepts the whole 0-100 range, so neither end may be read
    as "no rollout asked for": the task asked to stage, and vivo cannot stage anything."""
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(VivoUpdateException, match="no staged rollout"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], rollout_rate, submit=True)


@pytest.mark.asyncio
async def test_multiple_apks_are_refused(responses_mock, apk):
    """A vivo app holds one APK per version. Uploading one of a multi-architecture set
    would publish that architecture to every user."""
    fd, metadata = apk
    second = (fd, apk_metadata(architecture="x86_64"))

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(VivoUpdateException) as exc:
            await vivo.upload_apks(PACKAGE_NAME, [apk, second], None, submit=True)

    message = str(exc.value)
    assert "single APK per app version" in message
    assert "2 were given" in message
    assert fd.name in message
    assert recorded_calls(responses_mock) == []


@pytest.mark.asyncio
async def test_no_apks_is_refused(responses_mock):
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(VivoUpdateException, match="0 were given"):
            await vivo.upload_apks(PACKAGE_NAME, [], None, submit=True)


@pytest.mark.asyncio
async def test_dry_run_uploads_nothing(responses_mock, apk):
    # Having the `responses_mock` fixture in the test makes sure that this whole test doesn't try to contact any server
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET, dry_run=True) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    assert recorded_calls(responses_mock) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "apks,rollout_rate,expected",
    (
        pytest.param([True], 10, "no staged rollout", id="rollout"),
        pytest.param([True, True], None, "single APK per app version", id="multiple_apks"),
    ),
)
async def test_a_dry_run_still_rejects_what_can_never_be_published(responses_mock, apk, apks, rollout_rate, expected):
    """Both checks run before the dry-run bail-out, so a task that can never be committed
    fails on a dry run too."""
    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET, dry_run=True) as vivo:
        with pytest.raises(VivoUpdateException, match=expected):
            await vivo.upload_apks(PACKAGE_NAME, [apk] * len(apks), rollout_rate, submit=True)


@pytest.mark.asyncio
async def test_the_fallback_reaches_the_bind_request(responses_mock, apk):
    """End to end: a CLI-supplied value lands in the app.update.basic.info request when
    the store reports nothing for that field."""
    fd, _metadata_ = apk
    responses_mock.post(ROUTER_URL, payload=app_detail(languageCodes=None))
    responses_mock.post(ROUTER_URL, payload=upload_success(fd.name))
    responses_mock.post(ROUTER_URL, payload=success())

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET, basic_info_fallback={"language_codes": "en_in,ms"}) as vivo:
        await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=False)

    assert recorded_calls(responses_mock)[2].kwargs["data"]["languageCodes"] == "en_in,ms"


@pytest.mark.asyncio
async def test_a_missing_basic_info_field_fails_before_the_upload(responses_mock, apk):
    """The whole point of resolving before uploading: a gap costs one round trip, not a
    multi-hundred-megabyte upload that cannot then be bound."""
    responses_mock.post(ROUTER_URL, payload=app_detail(languageCodes=None))

    async with VivoAppStore(ACCESS_KEY, ACCESS_SECRET) as vivo:
        with pytest.raises(VivoContentInfoException, match="languageCodes"):
            await vivo.upload_apks(PACKAGE_NAME, [apk], None, submit=True)

    assert _methods_called(responses_mock) == [METHOD_APP_DETAIL]
