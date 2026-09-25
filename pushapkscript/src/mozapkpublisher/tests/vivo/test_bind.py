import pytest

from .common import ROUTER_URL, app_detail, business_failure, posted_params, success
from mozapkpublisher.vivo_api import METHOD_UPDATE_BASIC_INFO, VivoAppStoreApi
from mozapkpublisher.vivo_api.content_info import AppContentInfo
from mozapkpublisher.vivo_api.error import VivoContentInfoException, VivoException

PACKAGE_NAME = "org.mozilla.firefox"
DETAIL = app_detail()["data"]


def test_payload_carries_the_apk_serial_number():
    """The whole point of this interface: `apk` is what binds the uploaded binary."""
    payload = AppContentInfo(DETAIL).as_basic_info_payload(PACKAGE_NAME, "serial-1")

    assert payload["apk"] == "serial-1"
    assert payload["packageName"] == PACKAGE_NAME


def test_payload_joins_the_array_fields():
    """`app.detail` returns these as arrays but `app.update.basic.info` wants one
    comma-separated string. Sending the array would fail with A0334/A0335."""
    payload = AppContentInfo(DETAIL).as_basic_info_payload(PACKAGE_NAME, "serial-1")

    assert payload["languageCodes"] == "en_in,ms"
    assert payload["nationCodes"] == "in,id"


def test_payload_passes_through_already_joined_values():
    payload = AppContentInfo(app_detail(languageCodes="en_in", nationCodes="in")["data"]).as_basic_info_payload(PACKAGE_NAME, "s")

    assert payload["languageCodes"] == "en_in"
    assert payload["nationCodes"] == "in"


def test_payload_preserves_the_optional_listing_fields():
    """This interface replaces the basic-info record rather than patching it, so the
    optional fields have to be echoed back or the update risks clearing them."""
    payload = AppContentInfo(DETAIL).as_basic_info_payload(PACKAGE_NAME, "serial-1")

    assert payload["categoryId"] == 80000006
    assert payload["website"] == "https://mozilla.org"
    assert payload["phone"] == "1234567890"
    assert payload["iarc"] == 12
    assert payload["privacyStatement"] == "https://mozilla.org/privacy"


def test_payload_omits_optional_fields_the_app_does_not_have():
    detail = app_detail()["data"]
    del detail["website"]
    detail["phone"] = None

    payload = AppContentInfo(detail).as_basic_info_payload(PACKAGE_NAME, "serial-1")

    assert "website" not in payload
    assert "phone" not in payload


def test_payload_never_echoes_copyrights():
    """`app.detail` returns `copyrights` as URLs to the stored certificates, while this
    interface expects uploaded-file references. They are not the same value."""
    detail = app_detail(copyRights=["https://vivo.example/cert1.png"])["data"]

    payload = AppContentInfo(detail).as_basic_info_payload(PACKAGE_NAME, "serial-1")

    assert "copyRights" not in payload
    assert "copyrights" not in payload


@pytest.mark.parametrize("missing", ("languageCodes", "nationCodes", "email"))
def test_missing_mandatory_field_is_caught_locally(missing):
    """Caught before the request goes out, because the store would otherwise reject it
    with A0313/A0314/A0315 only after the APK had already been uploaded."""
    detail = app_detail()["data"]
    del detail[missing]

    with pytest.raises(VivoContentInfoException, match=missing):
        AppContentInfo(detail)


@pytest.mark.parametrize("empty", ([], "", None))
def test_empty_mandatory_field_is_caught_locally(empty):
    detail = app_detail(languageCodes=empty)["data"]

    with pytest.raises(VivoContentInfoException, match="languageCodes"):
        AppContentInfo(detail)


@pytest.mark.asyncio
async def test_update_basic_info_posts_the_bind(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=success())

    await vivo.update_basic_info(PACKAGE_NAME, "serial-1", AppContentInfo(DETAIL))

    params = posted_params(responses_mock)
    assert params["method"] == METHOD_UPDATE_BASIC_INFO
    assert params["apk"] == "serial-1"
    assert params["packageName"] == PACKAGE_NAME
    assert params["languageCodes"] == "en_in,ms"
    assert params["email"] == "release@mozilla.com"


@pytest.mark.asyncio
async def test_the_bind_names_the_app_the_caller_asked_for(vivo, responses_mock):
    """The payload is rebuilt from `app.detail`, which reports no `packageName` before a
    first-ever publish. The bind is the one interface that cannot go out without one."""
    responses_mock.post(ROUTER_URL, payload=success())
    info = AppContentInfo(app_detail(packageName=None)["data"], fallback={"email": "release@mozilla.com"})

    await vivo.update_basic_info(PACKAGE_NAME, "serial-1", info)

    assert posted_params(responses_mock)["packageName"] == PACKAGE_NAME


@pytest.mark.asyncio
async def test_update_basic_info_surfaces_a_refusal(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, payload=business_failure("A0109", "The uploaded app file does not exist"))

    with pytest.raises(VivoException, match="does not exist"):
        await vivo.update_basic_info(PACKAGE_NAME, "serial-1", AppContentInfo(DETAIL))


@pytest.mark.asyncio
async def test_a_bad_app_detail_fails_before_any_request(vivo, responses_mock):
    detail = app_detail()["data"]
    del detail["email"]

    with pytest.raises(VivoContentInfoException):
        await vivo.update_basic_info(PACKAGE_NAME, "serial-1", AppContentInfo(detail))

    assert responses_mock.requests == {}


def _detail_without(*keys):
    detail = app_detail()["data"]
    for key in keys:
        del detail[key]
    return detail


def test_a_fallback_fills_a_field_the_store_does_not_report():
    """The first-ever publish case: `app.create` writes no basic-info record, so the
    store reports nothing and the caller has to supply it."""
    info = AppContentInfo(_detail_without("languageCodes"), fallback={"language_codes": "en_in,ms"})

    assert info.as_basic_info_payload(PACKAGE_NAME, "s")["languageCodes"] == "en_in,ms"


def test_the_store_wins_over_a_differing_fallback():
    """Fallback, never override. This interface replaces the whole record, so a stale
    value winning over the store could drop countries from a live listing."""
    info = AppContentInfo(app_detail()["data"], fallback={"nation_codes": "au,pl", "email": "stale@example.com"})

    payload = info.as_basic_info_payload(PACKAGE_NAME, "s")
    assert payload["nationCodes"] == "in,id"
    assert payload["email"] == "release@mozilla.com"


def test_resolution_is_per_field():
    """A partially populated record only needs its gaps filled."""
    info = AppContentInfo(_detail_without("nationCodes"), fallback={"nation_codes": ["in", "id"], "language_codes": "ignored"})

    payload = info.as_basic_info_payload(PACKAGE_NAME, "s")
    assert payload["nationCodes"] == "in,id"
    assert payload["languageCodes"] == "en_in,ms"


def test_a_fallback_accepts_a_list_or_a_comma_separated_string():
    as_list = AppContentInfo(_detail_without("nationCodes"), fallback={"nation_codes": ["in", "id"]})
    as_string = AppContentInfo(_detail_without("nationCodes"), fallback={"nation_codes": "in,id"})

    assert as_list.as_basic_info_payload(PACKAGE_NAME, "s")["nationCodes"] == "in,id"
    assert as_string.as_basic_info_payload(PACKAGE_NAME, "s")["nationCodes"] == "in,id"


def test_nation_codes_is_never_derived_from_nations():
    """`nations` reports per-country publication status including removed countries, and
    vivo's own example has it disagreeing with `nationCodes` (bd/bn vs in/id)."""
    detail = _detail_without("nationCodes")
    detail["nations"] = [{"nationCode": "bd", "onlineStatus": 0}, {"nationCode": "bn", "onlineStatus": 2}]

    with pytest.raises(VivoContentInfoException, match="nationCodes"):
        AppContentInfo(detail)


def test_every_missing_field_is_reported_at_once():
    """Reporting one at a time means an operator fixes them one run at a time."""
    with pytest.raises(VivoContentInfoException) as exc:
        AppContentInfo(_detail_without("languageCodes", "nationCodes", "email"))

    message = str(exc.value)
    for key in ("languageCodes", "nationCodes", "email"):
        assert key in message
    # And it names the `basic_info_fallback` key for each, so the fix is in the error.
    for key in ("language_codes", "nation_codes", "email"):
        assert repr(key) in message


def test_the_error_lists_the_keys_the_store_did_return():
    """The real unknown is what `app.detail` actually returns. Keys only -- the payload
    carries the contact email."""
    with pytest.raises(VivoContentInfoException) as exc:
        AppContentInfo(_detail_without("languageCodes"))

    message = str(exc.value)
    assert "'nationCodes'" in message and "'categoryId'" in message
    assert "release@mozilla.com" not in message


def test_an_empty_app_detail_is_reported_differently():
    """An empty payload means a wrong package name or bad credentials, not an
    unprovisioned app. Those are completely different fixes."""
    with pytest.raises(VivoContentInfoException, match="no app record at all"):
        AppContentInfo({})


def test_using_a_fallback_warns_that_it_writes_to_the_live_listing(caplog):
    with caplog.at_level("WARNING"):
        AppContentInfo(_detail_without("email"), fallback={"email": "release@mozilla.com"})

    assert "reported no 'email'" in caplog.text
    assert "live listing" in caplog.text


def test_no_warning_when_the_store_supplies_everything(caplog):
    with caplog.at_level("WARNING"):
        AppContentInfo(app_detail()["data"], fallback={"email": "unused@example.com"})

    assert caplog.text == ""


# --- default language ordering -------------------------------------------------------
#
# Interface 8 reads the entry before the first comma as the default language, while
# `app.detail` returns `languageCodes` as an unordered array plus a separate
# `defaultLanguageCode`. Joining in arrival order silently re-declares the default.


def _detail(language_codes, default=None):
    detail = app_detail()["data"]
    detail["languageCodes"] = language_codes
    if default is None:
        detail.pop("defaultLanguageCode", None)
    else:
        detail["defaultLanguageCode"] = default
    return detail


def test_the_stores_default_language_is_sent_first():
    """'hi' is the app's default but second in the array; joining in arrival order would
    demote it to 'en_in'."""
    info = AppContentInfo(_detail(["en_in", "hi"], default="hi"))

    assert info.as_basic_info_payload(PACKAGE_NAME, "s")["languageCodes"] == "hi,en_in"


def test_a_default_already_first_is_left_alone():
    info = AppContentInfo(_detail(["hi", "en_in"], default="hi"))

    assert info.as_basic_info_payload(PACKAGE_NAME, "s")["languageCodes"] == "hi,en_in"


def test_reordering_preserves_every_language():
    """Moving the default to the head must not drop or duplicate any other language."""
    info = AppContentInfo(_detail(["en_in", "ms", "hi", "th"], default="hi"))

    codes = info.as_basic_info_payload(PACKAGE_NAME, "s")["languageCodes"].split(",")
    assert codes[0] == "hi"
    assert sorted(codes) == ["en_in", "hi", "ms", "th"]
    assert len(codes) == len(set(codes))


def test_no_declared_default_leaves_the_resolved_order_alone():
    """A first-ever publish has no default to preserve, so the caller's order stands and
    its first entry becomes the default."""
    info = AppContentInfo(_detail(["en_in", "ms"]))

    assert info.as_basic_info_payload(PACKAGE_NAME, "s")["languageCodes"] == "en_in,ms"


def test_a_supplied_order_is_the_declaration_when_the_store_has_no_default():
    """This is how `--vivo-language-codes en_in,hi` makes en_in the default."""
    detail = _detail(["en_in"])
    del detail["languageCodes"]

    info = AppContentInfo(detail, fallback={"language_codes": "en_in,hi"})

    assert info.as_basic_info_payload(PACKAGE_NAME, "s")["languageCodes"] == "en_in,hi"


def test_a_default_the_store_does_not_list_warns_instead_of_being_added(caplog):
    """Adding it would declare a language with no materials and fail the submit with
    A0311, so the mismatch is reported rather than silently repaired."""
    with caplog.at_level("WARNING"):
        info = AppContentInfo(_detail(["en_in", "ms"], default="hi"))
        payload = info.as_basic_info_payload(PACKAGE_NAME, "s")

    assert payload["languageCodes"] == "en_in,ms"
    assert "hi" not in payload["languageCodes"].split(",")
    assert "A0311" in caplog.text


def test_a_comma_separated_string_from_the_store_is_also_ordered():
    """Defensive: the store is documented to return an array, but a joined string must
    not bypass the ordering."""
    info = AppContentInfo(_detail("en_in,hi", default="hi"))

    assert info.as_basic_info_payload(PACKAGE_NAME, "s")["languageCodes"] == "hi,en_in"


@pytest.mark.parametrize("empty", ([], "", ",", " , "))
def test_a_code_list_that_normalises_to_nothing_counts_as_missing(empty):
    """`--vivo-language-codes ','` is not a language set."""
    with pytest.raises(VivoContentInfoException, match="languageCodes"):
        AppContentInfo(_detail(empty))
