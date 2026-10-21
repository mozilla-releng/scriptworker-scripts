import copy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .error import SgsContentInfoException

# This is a list of key that we know the API gets angry about if they're missing
MANDATORY_CONTENT_INFO_KEYS = [
    "binaryList",
    "contentId",
    "defaultLanguageCode",
    "paid",
    "publicationType",
]

# `publicationType` values. See
# https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/reference.html
PUBLICATION_TYPE_ON_DATE = "02"
PUBLICATION_TYPE_MANUAL = "03"

# Format of `startPublicationDate`. Seller Portal reads publication dates as GMT, so the
# date is converted to UTC before it is formatted.
START_PUBLICATION_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


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
                raise SgsContentInfoException("The app content info is missing a mandatory key: {}".format(key))

    @property
    def binary_list(self):
        """
        Return the binary list for this content info
        """
        return self._inner["binaryList"]

    @property
    def content_id(self):
        """
        Return the content ID for this content info
        """
        return self._inner["contentId"]

    @property
    def status(self):
        """
        Return the status for this content info
        """
        return self._inner["contentStatus"]

    def as_new_data(self, scheduled_release_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Return this content info as a dictionary ready to be sent to the `updateContent` API.
        The following transformations are applied:
            - The `binaryList` field is removed as the `contentUpdate` API does not accept it when modified. Binaries are managed through their own API.
            - The `screenshots`, `addLanguage` and `sellCountryList` are nulled out as we don't support updating them and can't send them back verbatim.
            - Without `scheduled_release_date`, the `startPublicationDate` field is removed and the `publicationType` is set to "03" to set the
              publication time to "manual"
            - With `scheduled_release_date`, the `publicationType` is set to "02" and `startPublicationDate` to that date, so the app goes
              on sale then, once it has passed review
        """
        self.validate()

        content = copy.copy(self._inner)

        # Sometimes having this fails... Sometimes it doesn't... It makes no sense but removing it completely makes the content info upload not fail 🤷
        if "startPublicationDate" in content:
            del content["startPublicationDate"]

        if "binaryList" in content:
            del content["binaryList"]

        # All those need to be None so samsung knows we're not trying to update
        # them. Leaving them as is *should* be doing the same thing as we're
        # just sending back what we got, except it doesn't work and returns
        # errors about dates needing to be in the future. There's no date
        # anywhere in those...
        content["screenshots"] = None
        content["addLanguage"] = None
        content["sellCountryList"] = None

        if scheduled_release_date is None:
            content["publicationType"] = PUBLICATION_TYPE_MANUAL
        else:
            content["publicationType"] = PUBLICATION_TYPE_ON_DATE
            content["startPublicationDate"] = scheduled_release_date.astimezone(timezone.utc).strftime(START_PUBLICATION_DATE_FORMAT)

        return content
