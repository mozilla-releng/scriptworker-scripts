from typing import Dict, Any
from .error import SgsContentInfoException
import copy

# This is a list of key that we know the API gets angry about if they're missing
MANDATORY_CONTENT_INFO_KEYS = [
    "binaryList",
    "contentId",
    "defaultLanguageCode",
    "paid",
    "publicationType",
]


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
                raise SgsContentInfoException(
                    "The app content info is missing a mandatory key: {}".format(key)
                )

        if len(self._inner.get("binaryList", [])) > 20:
            raise SgsContentInfoException(
                "You cannot have more than 20 binaries declared for a single content ID"
            )

    def add_binary(self, new_binary):
        """
        Add a binary to the binary list for this content info. If the list would exceed 20 items, the first item is popped from the list.
        This is because the samsung API doesn't want an app to have more than 20 binaries registered at the same time.
        """
        binaryList = self._inner.setdefault("binaryList", [])

        # Samsung only allows 20 binaries to be uploaded for a certain content ID
        # Remove older binaries so that we get space to add our own
        while len(binaryList) >= 20:
            binaryList.pop(0)

        binaryList.append(new_binary)

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

    def as_new_data(self) -> Dict[str, Any]:
        """
        Return this content info as a dictionary ready to be sent to the `updateContent` API.
        The following transformations are applied:
            - The `startPublicationDate` field is removed
            - The `screenshots`, `addLanguage` and `sellCountryList` are nulled out as we don't support updating them and can't send them back verbatim.
            - The `publicationType` is set to "03" to set the publication time to "manual"
        """
        self.validate()

        content = copy.copy(self._inner)

        # Sometimes having this fails... Sometimes it doesn't... It makes no sense but removing it completely makes the content info upload not fail 🤷
        if "startPublicationDate" in content:
            del content["startPublicationDate"]

        # All those need to be None so samsung knows we're not trying to update
        # them. Leaving them as is *should* be doing the same thing as we're
        # just sending back what we got, except it doesn't work and returns
        # errors about dates needing to be in the future. There's no date
        # anywhere in those...
        content["screenshots"] = None
        content["addLanguage"] = None
        content["sellCountryList"] = None

        # Set the publication time to manual
        # See https://developer.samsung.com/galaxy-store/galaxy-store-developer-api/content-publish-api/reference.html
        content["publicationType"] = "03"

        return content
