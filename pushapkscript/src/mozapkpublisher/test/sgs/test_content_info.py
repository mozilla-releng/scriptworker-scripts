import copy
import pytest
from contextlib import nullcontext as does_not_raise

from .common import basic_auth_headers
from mozapkpublisher.sgs_api.content_info import AppContentInfo
from mozapkpublisher.sgs_api.error import (
    SgsAuthenticationException,
    SgsContentInfoException,
)


CONTENT_INFO_DEFAULTS = {
    "defaultLanguageCode": "EN",
    "paid": "N",
    "publicationType": "03",
    "binaryList": [],
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            401,
            {"code": "AUTH_REQUIRE", "message": "Invalid accessToken", "from": "asgw"},
            pytest.raises(SgsAuthenticationException, match="Invalid accessToken"),
        ),
        pytest.param(
            401,
            {
                "code": "AUTH_REQUIRE",
                "message": "Not found serviceAccount by serviceAccountId",
                "from": "asgw",
            },
            pytest.raises(SgsAuthenticationException, match="Not found serviceAccount"),
        ),
        pytest.param(
            200, [], pytest.raises(SgsContentInfoException, match="got 0, expected >=1")
        ),
        pytest.param(
            200,
            [{"contentId": "foo"}],
            pytest.raises(SgsContentInfoException, match="another content ID"),
        ),
        pytest.param(
            200,
            [{"contentId": "barbaz", **CONTENT_INFO_DEFAULTS}],
            pytest.raises(
                SgsContentInfoException,
                match="another content ID than the one given: barbaz",
            ),
        ),
        pytest.param(
            200, [{"contentId": "foobar", **CONTENT_INFO_DEFAULTS}], does_not_raise()
        ),
    ),
)
async def test_get_content_info(sgs, responses_mock, status, response, expectation):
    responses_mock.get(
        "https://devapi.samsungapps.com/seller/contentInfo?contentId=foobar",
        status=status,
        payload=response,
    )
    with expectation as exc:
        res = await sgs.get_content_info("foobar")

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/seller/contentInfo",
        method="GET",
        params={"contentId": "foobar"},
        headers=basic_auth_headers(),
    )

    if exc is None:
        assert len(res) == 1
        assert res[0].content_id == "foobar"


MINIMAL_VALID_CONTENT_INFO = {
    "binaryList": [],
    "contentId": 0,
    "defaultLanguageCode": "FR",
    "paid": "N",
    "publicationType": "03",
}


def test_adding_more_than_twenty_binaries():
    new_content_info = copy.copy(MINIMAL_VALID_CONTENT_INFO)
    new_content_info["binaryList"] = [{"fileName": str(i)} for i in range(21)]

    with pytest.raises(SgsContentInfoException, match="more than 20 binaries"):
        content_info = AppContentInfo(new_content_info)

    new_content_info["binaryList"] = [{"fileName": str(i)} for i in range(20)]
    content_info = AppContentInfo(new_content_info)

    assert len(content_info.binary_list) == 20
    content_info.add_binary({"fileName": "foo"})
    assert len(content_info.binary_list) == 20
    assert content_info.binary_list[0]["fileName"] == "1"
    assert content_info.binary_list[-1]["fileName"] == "foo"


@pytest.mark.parametrize("key", (None, *MINIMAL_VALID_CONTENT_INFO.keys()))
def test_creating_content_info_with_missing_key(key):
    new_content_info = copy.copy(MINIMAL_VALID_CONTENT_INFO)
    if key is not None:
        del new_content_info[key]

        with pytest.raises(SgsContentInfoException, match=key):
            AppContentInfo(new_content_info)
    else:
        AppContentInfo(new_content_info)


def test_new_content_info_sets_publication_type_to_manual():
    new_content_info = copy.copy(MINIMAL_VALID_CONTENT_INFO)
    new_content_info["publicationType"] = "00"
    content_info = AppContentInfo(new_content_info)
    assert content_info.as_new_data()["publicationType"] == "03"
