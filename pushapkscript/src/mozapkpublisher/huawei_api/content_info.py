from typing import Dict, Any, List
from .error import HuaweiContentInfoException

# This is a list of keys we expect the GET app-info response to surface.
MANDATORY_CONTENT_INFO_KEYS = [
    "appId",
]

# `fileType` value for an Android RPK/APK/AAB binary in the app-file-info payload.
FILE_TYPE_ANDROID_BINARY = 5


class AppContentInfo:
    def __init__(self, content: Dict[str, Any]):
        self._inner = content
        self.validate()

    def validate(self) -> None:
        """
        Validate that the content info looks correct.
        """
        for key in MANDATORY_CONTENT_INFO_KEYS:
            if key not in self._inner:
                raise HuaweiContentInfoException(
                    "The app content info is missing a mandatory key: {}".format(key)
                )

    @property
    def app_id(self):
        """
        Return the app ID for this content info
        """
        return self._inner["appId"]

    @property
    def status(self):
        """
        Return the release status for this content info
        """
        return self._inner.get("releaseState")

    def as_file_info_payload(self, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Build the body for `PUT /api/publish/v2/app-file-info`. `files` is a list of
        `{"fileName": ..., "fileDestUrl": ...}` entries (`fileDestUrl` is returned by
        the upload step).
        """
        return {
            "fileType": FILE_TYPE_ANDROID_BINARY,
            "files": files,
        }
