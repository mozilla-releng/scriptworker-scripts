import copy
import os
import pytest

from aioresponses import aioresponses
from mozapkpublisher.push_apk import push_apk
from mozapkpublisher.sgs_api.error import SgsUpdateException
from ..sgs.common import basic_auth_headers
import mozapkpublisher


FIREFOX_CONTENT_INFO = {
    "contentId": "000002975732",
    "appTitle": "Firefox Browser: fast, private & safe web browser",
    "icon": "https://img.samsungapps.com/content/0jkrs7j2vc/2020/0529/IconImage_20200529133545703.png",
    "iconKey": None,
    "contentStatus": "FOR_SALE",
    "defaultLanguageCode": "ENG",
    "applicationType": "android",
    "longDescription": "long",
    "shortDescription": "short",
    "newFeature": "",
    "ageLimit": "4",
    "chinaAgeLimit": None,
    "openSourceURL": "",
    "privatePolicyURL": "https://www.mozilla.org/privacy/firefox/",
    "termAndConditionURL": None,
    "youTubeURL": "http://www.youtube.com/watch?v=firefoxchan",
    "copyrightHolder": "",
    "supportEMail": "firefox-android-feedback@mozilla.com",
    "supportedSiteUrl": "",
    "binaryList": [
        {
            "fileName": "App_20250326124829647.apk",
            "binarySeq": "340",
            "versionCode": "2016081312",
            "versionName": "137.0",
            "packageName": "org.mozilla.firefox",
            "nativePlatforms": "32bit",
            "apiminSdkVersion": "21",
            "apimaxSdkVersion": None,
            "iapSdk": "N",
            "gms": "Y",
            "filekey": None,
        },
        {
            "fileName": "App_20250326124836815.apk",
            "binarySeq": "341",
            "versionCode": "2016081314",
            "versionName": "137.0",
            "packageName": "org.mozilla.firefox",
            "nativePlatforms": "64bit",
            "apiminSdkVersion": "21",
            "apimaxSdkVersion": None,
            "iapSdk": "N",
            "gms": "Y",
            "filekey": None,
        },
    ],
    "standardPrice": "0",
    "paid": "N",
    "publicationType": "03",
    "startPublicationDate": "2025-04-01 00:00:00",
    "stopPublicationDate": "9999-12-31",
    "usExportLaws": True,
    "reviewComment": None,
    "reviewFilename": None,
    "reviewFilekey": None,
    "edgescreen": None,
    "edgescreenKey": None,
    "edgescreenplus": None,
    "edgescreenplusKey": None,
    "notifyResult": [],
    "sellCountryList": [
        {"countryCode": "ARE", "price": "0"},
        {"countryCode": "ARG", "price": "0"},
    ],
    "supportedLanguages": ["DEU", "ENG", "FRA", "KOR"],
    "addLanguage": [],
    "screenshots": [],
    "category": [
        {"name": "Others", "type": "ONE_DEPTH_CATEGORY"},
        {"name": "Tool", "type": "GENERAL_CATEGORY"},
    ],
    "heroImage": None,
    "heroImageKey": None,
}

FOCUS_CONTENT_INFO = {
    "contentId": "000003397900",
    "appTitle": "Firefox Focus: The Companion Browser",
    "icon": "https://img.samsungapps.com/content/0jkrs7j2vc/2021/1014/IconImage_20211014134035764.png",
    "iconKey": None,
    "contentStatus": "FOR_SALE",
    "defaultLanguageCode": "ENG",
    "applicationType": "android",
    "longDescription": "long",
    "shortDescription": "short",
    "newFeature": "",
    "ageLimit": "4",
    "chinaAgeLimit": None,
    "openSourceURL": "",
    "privatePolicyURL": "https://www.mozilla.org/privacy/firefox-focus/",
    "termAndConditionURL": None,
    "youTubeURL": "",
    "copyrightHolder": "",
    "supportEMail": "android-marketplace-notices@mozilla.com",
    "supportedSiteUrl": "",
    "binaryList": [
        {
            "fileName": "App_20250326114753061.apk",
            "binarySeq": "304",
            "versionCode": "390842046",
            "versionName": "137.0",
            "packageName": "org.mozilla.focus",
            "nativePlatforms": "32bit",
            "apiminSdkVersion": "21",
            "apimaxSdkVersion": None,
            "iapSdk": "N",
            "gms": "Y",
            "filekey": None,
        },
        {
            "fileName": "App_20250326114759363.apk",
            "binarySeq": "305",
            "versionCode": "390842048",
            "versionName": "137.0",
            "packageName": "org.mozilla.focus",
            "nativePlatforms": "64bit",
            "apiminSdkVersion": "21",
            "apimaxSdkVersion": None,
            "iapSdk": "N",
            "gms": "Y",
            "filekey": None,
        },
    ],
    "standardPrice": "0",
    "paid": "N",
    "publicationType": "03",
    "startPublicationDate": "2025-04-01 00:00:00",
    "stopPublicationDate": "9999-12-31",
    "usExportLaws": True,
    "reviewComment": None,
    "reviewFilename": None,
    "reviewFilekey": None,
    "edgescreen": None,
    "edgescreenKey": None,
    "edgescreenplus": None,
    "edgescreenplusKey": None,
    "notifyResult": [],
    "sellCountryList": [
        {"countryCode": "ARE", "price": "0"},
        {"countryCode": "ARG", "price": "0"},
    ],
    "supportedLanguages": ["DEU", "ENG", "FRA", "KOR"],
    "addLanguage": [],
    "screenshots": [],
    "category": [
        {"name": "Others", "type": "ONE_DEPTH_CATEGORY"},
        {"name": "Tool", "type": "GENERAL_CATEGORY"},
        {"name": "Other", "type": "EXCLUSIVE_ONE_CATEGORY"},
    ],
    "heroImage": None,
    "heroImageKey": None,
}

UPDATED_FOCUS_CONTENT_INFO = copy.deepcopy(FOCUS_CONTENT_INFO)
UPDATED_FOCUS_CONTENT_INFO["contentStatus"] = "UPDATING"
UPDATED_FOCUS_CONTENT_INFO["binaryList"].append(
    {
        "fileName": "App_20250326114753061.apk",
        "binarySeq": "306",
        "versionCode": "390842050",
        "versionName": "137.0.2",
        "packageName": "org.mozilla.focus",
        "nativePlatforms": "32bit",
        "apiminSdkVersion": "21",
        "apimaxSdkVersion": None,
        "iapSdk": "N",
        "gms": "Y",
        "filekey": None,
    }
)


def setup_default_sgs_api(responses):
    responses.get(
        "https://devapi.samsungapps.com/seller/contentList",
        status=200,
        payload=[
            {
                "contentName": "Firefox Browser: fast, private & safe web browser",
                "contentId": "000002975732",
                "contentStatus": "FOR_SALE",
                "standardPrice": "0",
                "paid": "N",
                "modifyDate": "2025-04-14 16:03:35.0",
            },
            {
                "contentName": "Firefox Focus: The Companion Browser",
                "contentId": "000003397900",
                "contentStatus": "FOR_SALE",
                "standardPrice": "0",
                "paid": "N",
                "modifyDate": "2025-04-01 13:49:18.0",
            },
        ],
    )

    # Only repeat the response once so we can fake an upload changing binaryList.
    responses.get(
        "https://devapi.samsungapps.com/seller/contentInfo?contentId=000002975732",
        repeat=1,
        status=200,
        payload=[FIREFOX_CONTENT_INFO],
    )
    responses.get(
        "https://devapi.samsungapps.com/seller/contentInfo?contentId=000003397900",
        repeat=2,
        status=200,
        payload=[FOCUS_CONTENT_INFO],
    )

    responses.get(
        "https://devapi.samsungapps.com/seller/contentInfo?contentId=000003397900",
        status=200,
        payload=[UPDATED_FOCUS_CONTENT_INFO, FOCUS_CONTENT_INFO],
    )

    responses.post(
        "https://devapi.samsungapps.com/seller/createUploadSessionId",
        status=200,
        payload={"sessionId": "789"},
    )
    responses.post(
        "https://seller.samsungapps.com/galaxyapi/fileUpload",
        status=200,
        payload={"fileKey": "abc", "fileSize": 15},
    )
    responses.post("https://devapi.samsungapps.com/seller/contentUpdate", status=200)
    responses.put(
        "https://devapi.samsungapps.com/seller/v2/content/stagedRolloutBinary",
        status=200,
    )
    responses.put(
        "https://devapi.samsungapps.com/seller/v2/content/stagedRolloutRate", status=200
    )
    responses.post("https://devapi.samsungapps.com/seller/contentSubmit", status=200)


@pytest.fixture
def responses():
    with aioresponses() as responses:
        yield responses


def fake_apk_metadata(files, *args, **kwargs):
    ret = {}
    for file in files:
        ret[open(file, "rb")] = {
            "package_name": "org.mozilla.focus",
            "api_level": 21,
            "version_code": "390842050",
            "version_name": "137.1",
            "architecture": "armeabi-v7a",
            "locales": ("fr", "en"),
        }

    return ret


class ExpectedFormData:
    def __init__(self):
        self.expected_fields = {}

    def __eq__(self, form):
        for ty_options, headers, value in form._fields:
            name = ty_options["name"]
            assert (
                name in self.expected_fields
            ), f"Unexpected field in form data: {name}"

            expected_field = self.expected_fields[name]
            expected_filename = expected_field["filename"]

            assert (
                expected_filename is None or "filename" in ty_options
            ), f"Was expecting filename for field {name} but it's missing"

            if "filename" in ty_options and expected_filename is not None:
                assert ty_options["filename"] == expected_filename

        return True

    def add_field(self, name, value, filename=None):
        self.expected_fields[name] = {"value": value, "filename": filename}
        return self


async def run_push_apk(monkeypatch, rollout_rate=None, submit=False):
    file = os.path.join(os.path.dirname(__file__), "../", "data", "blob")
    monkeypatch.setattr(
        mozapkpublisher.push_apk, "extract_and_check_apks_metadata", fake_apk_metadata
    )

    await push_apk(
        [file],
        None,
        ["org.mozilla.focus"],
        "release",
        store="samsung",
        rollout_percentage=rollout_rate,
        dry_run=False,
        contact_server=True,
        skip_check_ordered_version_codes=False,
        skip_check_multiple_locales=False,
        skip_check_same_locales=False,
        skip_checks_fennec=True,
        submit=submit,
        sgs_service_account_id="service_account_id",
        sgs_access_token="access_token",
    )


@pytest.mark.parametrize("rollout_rate", (25, None))
@pytest.mark.parametrize("submit", (True, False))
@pytest.mark.asyncio
async def test_update_ok(responses, monkeypatch, rollout_rate, submit):
    setup_default_sgs_api(responses)
    await run_push_apk(monkeypatch, rollout_rate, submit)

    expected_file_upload = (
        ExpectedFormData()
        .add_field("file", b"laksdjflsakjdf\n", filename="org.mozilla.focus-armeabi-v7a-137.1.apk")
        .add_field("sessionId", "789")
    )

    expected_content_update = {
        "contentId": "000003397900",
        "appTitle": "Firefox Focus: The Companion Browser",
        "icon": "https://img.samsungapps.com/content/0jkrs7j2vc/2021/1014/IconImage_20211014134035764.png",
        "iconKey": None,
        "contentStatus": "FOR_SALE",
        "defaultLanguageCode": "ENG",
        "applicationType": "android",
        "longDescription": "long",
        "shortDescription": "short",
        "newFeature": "",
        "ageLimit": "4",
        "chinaAgeLimit": None,
        "openSourceURL": "",
        "privatePolicyURL": "https://www.mozilla.org/privacy/firefox-focus/",
        "termAndConditionURL": None,
        "youTubeURL": "",
        "copyrightHolder": "",
        "supportEMail": "android-marketplace-notices@mozilla.com",
        "supportedSiteUrl": "",
        "binaryList": [
            {
                "fileName": "App_20250326114753061.apk",
                "binarySeq": "304",
                "versionCode": "390842046",
                "versionName": "137.0",
                "packageName": "org.mozilla.focus",
                "nativePlatforms": "32bit",
                "apiminSdkVersion": "21",
                "apimaxSdkVersion": None,
                "iapSdk": "N",
                "gms": "Y",
                "filekey": None,
            },
            {
                "fileName": "App_20250326114759363.apk",
                "binarySeq": "305",
                "versionCode": "390842048",
                "versionName": "137.0",
                "packageName": "org.mozilla.focus",
                "nativePlatforms": "64bit",
                "apiminSdkVersion": "21",
                "apimaxSdkVersion": None,
                "iapSdk": "N",
                "gms": "Y",
                "filekey": None,
            },
            {
                "fileName": "blob",
                "versionCode": "390842050",
                "binarySeq": 306,
                "packageName": "org.mozilla.focus",
                "apiminSdkVersion": 21,
                "apimaxSdkversion": None,
                "iapSdk": "N",
                "gms": "Y",
                "filekey": "abc",
            },
        ],
        "standardPrice": "0",
        "paid": "N",
        "publicationType": "03",
        "stopPublicationDate": "9999-12-31",
        "usExportLaws": True,
        "reviewComment": None,
        "reviewFilename": None,
        "reviewFilekey": None,
        "edgescreen": None,
        "edgescreenKey": None,
        "edgescreenplus": None,
        "edgescreenplusKey": None,
        "notifyResult": [],
        "sellCountryList": None,
        "supportedLanguages": ["DEU", "ENG", "FRA", "KOR"],
        "addLanguage": None,
        "screenshots": None,
        "category": [
            {"name": "Others", "type": "ONE_DEPTH_CATEGORY"},
            {"name": "Tool", "type": "GENERAL_CATEGORY"},
            {"name": "Other", "type": "EXCLUSIVE_ONE_CATEGORY"},
        ],
        "heroImage": None,
        "heroImageKey": None,
    }

    responses.assert_called_with(
        url="https://devapi.samsungapps.com/seller/contentList",
        method="GET",
        headers=basic_auth_headers(),
    )
    responses.assert_called_with(
        url="https://devapi.samsungapps.com/seller/contentInfo",
        params={"contentId": "000002975732"},
        method="GET",
        headers=basic_auth_headers(),
    )
    responses.assert_called_with(
        url="https://devapi.samsungapps.com/seller/contentInfo",
        params={"contentId": "000003397900"},
        method="GET",
        headers=basic_auth_headers(),
    )
    responses.assert_called_with(
        url="https://devapi.samsungapps.com/seller/createUploadSessionId",
        method="POST",
        headers=basic_auth_headers(),
    )
    responses.assert_called_with(
        url="https://seller.samsungapps.com/galaxyapi/fileUpload",
        method="POST",
        headers=basic_auth_headers(),
        data=expected_file_upload,
    )
    responses.assert_called_with(
        url="https://devapi.samsungapps.com/seller/contentUpdate",
        method="POST",
        headers=basic_auth_headers(),
        json=expected_content_update,
    )

    if rollout_rate is not None:
        responses.assert_called_with(
            url="https://devapi.samsungapps.com/seller/v2/content/stagedRolloutBinary",
            method="PUT",
            headers=basic_auth_headers(),
            json={"contentId": "000003397900", "function": "ADD", "binarySeq": "306"},
        )
        responses.assert_called_with(
            url="https://devapi.samsungapps.com/seller/v2/content/stagedRolloutRate",
            method="PUT",
            headers=basic_auth_headers(),
            json={
                "contentId": "000003397900",
                "function": "ENABLE_ROLLOUT",
                "appStatus": "REGISTRATION",
                "rolloutRate": 25,
            },
        )

    if submit:
        responses.assert_called_with(
            url="https://devapi.samsungapps.com/seller/contentSubmit",
            method="POST",
            headers=basic_auth_headers(),
            json={"contentId": "000003397900"},
        )


@pytest.mark.asyncio
async def test_update_when_app_in_wrong_state(responses, monkeypatch):
    responses.get(
        "https://devapi.samsungapps.com/seller/contentList",
        status=200,
        payload=[
            {
                "contentName": "Firefox Browser: fast, private & safe web browser",
                "contentId": "000002975732",
                "contentStatus": "FOR_SALE",
                "standardPrice": "0",
                "paid": "N",
                "modifyDate": "2025-04-14 16:03:35.0",
            },
            {
                "contentName": "Firefox Focus: The Companion Browser",
                "contentId": "000003397900",
                "contentStatus": "FOR_SALE",
                "standardPrice": "0",
                "paid": "N",
                "modifyDate": "2025-04-01 13:49:18.0",
            },
            {
                "contentName": "Firefox Focus: The Companion Browser",
                "contentId": "000003397900",
                "contentStatus": "UPDATING",
                "standardPrice": "0",
                "paid": "N",
                "modifyDate": "2025-04-01 13:49:18.0",
            },
        ],
    )

    responses.get(
        "https://devapi.samsungapps.com/seller/contentInfo?contentId=000002975732",
        status=200,
        payload=[FIREFOX_CONTENT_INFO],
    )

    responses.get(
        "https://devapi.samsungapps.com/seller/contentInfo?contentId=000003397900",
        status=200,
        repeat=True,
        payload=[FOCUS_CONTENT_INFO, UPDATED_FOCUS_CONTENT_INFO],
    )

    with pytest.raises(SgsUpdateException, match="cancel it manually"):
        await run_push_apk(monkeypatch)


@pytest.mark.asyncio
async def test_update_with_content_id_missing(responses, monkeypatch):
    responses.get(
        "https://devapi.samsungapps.com/seller/contentList", status=200, payload=[]
    )

    with pytest.raises(SgsUpdateException, match="Couldn't find a content ID"):
        await run_push_apk(monkeypatch)
