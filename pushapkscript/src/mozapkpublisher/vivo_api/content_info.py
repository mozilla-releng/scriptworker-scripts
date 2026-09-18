import logging
from typing import Any, Dict, List, Optional, Union

from .error import VivoContentInfoException

logger = logging.getLogger(__name__)

# `app.update.basic.info` is an update of the whole basic-info record rather than a patch
# of the one field we care about, so it rejects the request unless these are supplied
# alongside `apk`. They are normally read back from `app.detail` and re-sent unchanged.
MANDATORY_BASIC_INFO_KEYS = [
    "languageCodes",
    "nationCodes",
    "email",
]

# Maps each mandatory wire field to the key a caller supplies a fallback under. The
# caller-facing names are snake_case to match the CLI flags; the wire names are vivo's.
FALLBACK_KEYS = {
    "languageCodes": "language_codes",
    "nationCodes": "nation_codes",
    "email": "email",
}

# Optional fields `app.detail` returns in the same representation `app.update.basic.info`
# accepts, so they can be echoed back untouched. Re-sending them keeps the store listing
# as it was; omitting one risks the update clearing it.
PRESERVED_OPTIONAL_KEYS = [
    "categoryId",
    "website",
    "phone",
    "iarc",
    "privacyStatement",
]


# The two mandatory fields that are code lists rather than scalars. `app.detail` returns
# them as arrays and `app.update.basic.info` wants one comma-separated string, so they are
# normalized to a list on the way in and joined on the way out.
CODE_LIST_KEYS = ("languageCodes", "nationCodes")


def _as_code_list(value: Union[str, List[str]]) -> List[str]:
    """
    Normalize a code list to a list of codes, accepting either the array `app.detail`
    returns or the comma-separated string a caller supplies on the command line.
    """
    if isinstance(value, str):
        return [code.strip() for code in value.split(",") if code.strip()]
    return [code for code in value if code]


class AppContentInfo:
    """
    The basic-info record `app.update.basic.info` will be given, resolved from what the
    store reports and, only where the store reports nothing, from a caller-supplied
    fallback.

    The fallback never overrides a value the store has: this interface replaces the
    whole record, so a stale fallback winning could drop countries from a live listing.
    """

    def __init__(self, content: Dict[str, Any], fallback: Optional[Dict[str, Any]] = None):
        self._inner = content
        self._fallback = fallback or {}
        self._resolved, self._missing, self._from_fallback = self._resolve()
        self.validate()
        self._warn_about_fallbacks()

    def _resolve(self):
        """
        Resolve each mandatory field, per field, from the store first and then the
        fallback.

        `nationCodes` is NOT derived from the `nations` array, even though every entry
        there carries a `nationCode`: `nations` is per-country publication status,
        including countries the app was removed from, and vivo's own `app.detail`
        example has the two disagreeing (nations bd/bn, nationCodes in/id). Deriving it
        would change where this whole-record update publishes the app.
        """
        resolved, missing, from_fallback = {}, [], []

        for key in MANDATORY_BASIC_INFO_KEYS:
            value = self._normalise(key, self._inner.get(key))
            if value:
                resolved[key] = value
                continue

            fallback_value = self._normalise(key, self._fallback.get(FALLBACK_KEYS[key]))
            if fallback_value:
                resolved[key] = fallback_value
                from_fallback.append(key)
                continue

            missing.append(key)

        return resolved, missing, from_fallback

    @staticmethod
    def _normalise(key, value):
        """
        Normalise a field to the shape resolution compares on. A code list that
        normalises to nothing -- an empty array, or a string of nothing but separators --
        counts as absent rather than as a value worth sending.
        """
        if value and key in CODE_LIST_KEYS:
            return _as_code_list(value)
        return value

    def _language_codes(self) -> str:
        """
        Return `languageCodes` with the app's existing default language first.

        `app.update.basic.info` reads the entry before the first comma as the default
        language, while `app.detail` returns the codes unordered with the default in its
        own field. A default the store does not list is warned about rather than added:
        declaring a language with no materials fails the submit with A0311. With no
        default declared -- a first-ever publish -- the resolved order stands.
        """
        codes = list(self._resolved["languageCodes"])
        default = self._inner.get("defaultLanguageCode")

        if not default or codes[0] == default:
            return ",".join(codes)

        if default not in codes:
            logger.warning(
                "The vivo store reports '%s' as the default language for %s but does not list it among %s. It cannot be "
                "preserved, because declaring a language with no materials fails the submit with A0311, so the default "
                "language will become '%s'.",
                default,
                self.package_name,
                codes,
                codes[0],
            )
            return ",".join(codes)

        logger.info("Sending '%s' first to keep it the default language for %s.", default, self.package_name)

        return ",".join([default] + [code for code in codes if code != default])

    def validate(self) -> None:
        """
        Fail if a mandatory field came from neither the store nor the fallback.

        Every missing field is reported at once, with the keys `app.detail` did return,
        because the alternative is an operator fixing them one per run. Only the keys are
        listed, never the values -- the payload carries the contact email.
        """
        if not self._missing:
            return

        if not self._inner:
            detail = "`app.detail` returned no app record at all, which usually means a wrong package name, bad credentials, or a nonexistent app."
        else:
            detail = "`app.detail` returned these keys: {}.".format(sorted(self._inner.keys()))

        raise VivoContentInfoException(
            "Cannot build the `app.update.basic.info` request for {}, the only interface that binds an uploaded APK. "
            "It requires {}, which neither the store nor the supplied fallback provided. {} "
            "An app created with `app.create` has no basic-info record until one is written, so a first-ever publish "
            "has to supply these. Either set Language and Country/Region on the app in the vivo Developers console "
            "(preferred: the console stays authoritative), or supply {} in `basic_info_fallback`.".format(
                self._inner.get("packageName") or "the app",
                ", ".join(repr(key) for key in self._missing),
                detail,
                ", ".join(repr(FALLBACK_KEYS[key]) for key in self._missing),
            )
        )

    def _warn_about_fallbacks(self) -> None:
        for key in self._from_fallback:
            logger.warning(
                "`app.detail` reported no '%s'; using the supplied value %r instead. `app.update.basic.info` replaces "
                "the whole basic-info record, so this will be written to the live listing. Set it on the app in the "
                "vivo Developers console and stop passing it.",
                key,
                self._resolved[key],
            )

    @property
    def package_name(self):
        """
        Return the package name for this app detail
        """
        return self._inner.get("packageName")

    @property
    def status(self):
        """
        Return the app status (0 draft, 1 under review, 2 passed, 3 failed, 4 testing)
        """
        return self._inner.get("status")

    @property
    def version_code(self):
        """
        Return the version code of the APK the app currently holds
        """
        return self._inner.get("versionCode")

    def as_basic_info_payload(self, package_name: str, apk_serial_number: str) -> Dict[str, Any]:
        """
        Build the body for `app.update.basic.info`, the only interface that binds an
        uploaded APK to the app. `apk` is the `serialNumber` returned by
        `app.upload.apk`.

        `copyRights` is not echoed back: `app.detail` returns URLs to the stored
        certificates, while this interface expects references to uploaded files.
        """
        payload = {
            "packageName": package_name,
            "apk": apk_serial_number,
            "languageCodes": self._language_codes(),
            "nationCodes": ",".join(self._resolved["nationCodes"]),
            "email": self._resolved["email"],
        }

        for key in PRESERVED_OPTIONAL_KEYS:
            value = self._inner.get(key)
            if value is not None:
                payload[key] = value

        return payload
