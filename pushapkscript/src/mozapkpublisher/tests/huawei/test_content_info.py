import copy
import pytest

from mozapkpublisher.huawei_api.content_info import AppContentInfo
from mozapkpublisher.huawei_api.error import HuaweiContentInfoException


MINIMAL_VALID_CONTENT_INFO = {
    "appId": "appid-1",
    "releaseState": "Released",
}


def test_content_info_basic_accessors():
    content_info = AppContentInfo(copy.copy(MINIMAL_VALID_CONTENT_INFO))
    assert content_info.app_id == "appid-1"
    assert content_info.status == "Released"


@pytest.mark.parametrize("key", ("appId",))
def test_creating_content_info_with_missing_key(key):
    new_content_info = copy.copy(MINIMAL_VALID_CONTENT_INFO)
    del new_content_info[key]

    with pytest.raises(HuaweiContentInfoException, match=key):
        AppContentInfo(new_content_info)


def test_as_file_info_payload():
    content_info = AppContentInfo(copy.copy(MINIMAL_VALID_CONTENT_INFO))
    payload = content_info.as_file_info_payload(
        [{"fileName": "x.apk", "fileDestUrl": "https://example/x"}]
    )
    assert payload == {
        "fileType": 5,
        "files": [{"fileName": "x.apk", "fileDestUrl": "https://example/x"}],
    }
