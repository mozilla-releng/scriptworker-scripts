ALIASES_REGEXES = {
    "thunderbird-beta-latest": r"^Thunderbird-\d+\.0b\d+$",
    "thunderbird-beta-latest-ssl": r"^Thunderbird-\d+\.0b\d+-SSL$",
    "thunderbird-beta-msi-latest-ssl": r"^Thunderbird-\d+\.0b\d+-msi-SSL$",
    "thunderbird-beta-msix-latest-ssl": r"^Thunderbird-\d+\.0b\d+-msix-SSL$",
    "thunderbird-latest": r"^Thunderbird-\d+\.\d+(\.\d+)?$",
    "thunderbird-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?-SSL$",
    "thunderbird-msi-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?-msi-SSL$",
    "thunderbird-msix-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?-msix-SSL$",
    "thunderbird-esr-latest": r"^Thunderbird-\d+\.\d+(\.\d+)?esr$",
    "thunderbird-esr-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?esr-SSL$",
    "thunderbird-esr-msi-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?esr-msi-SSL$",
    "thunderbird-esr-msix-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?esr-msix-SSL$",
    "thunderbird-esr-next-latest": r"^Thunderbird-\d+\.\d+(\.\d+)?esr$",
    "thunderbird-esr-next-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?esr-SSL$",
    "thunderbird-esr-next-msi-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?esr-msi-SSL$",
    "thunderbird-esr-next-msix-latest-ssl": r"^Thunderbird-\d+\.\d+(\.\d+)?esr-msix-SSL$",
    "firefox-devedition-stub": r"^Devedition-\d+\.0b\d+-stub$",
    "firefox-devedition-latest": r"^Devedition-\d+\.0b\d+$",
    "firefox-devedition-latest-ssl": r"^Devedition-\d+\.0b\d+-SSL$",
    "firefox-devedition-msi-latest-ssl": r"^Devedition-\d+\.0b\d+-msi-SSL$",
    "firefox-devedition-msix-latest-ssl": r"^Devedition-\d+\.0b\d+-msix-SSL$",
    "firefox-beta-stub": r"^Firefox-\d+\.0b\d+-stub$",
    "firefox-beta-latest": r"^Firefox-\d+\.0b\d+$",
    "firefox-beta-latest-ssl": r"^Firefox-\d+\.0b\d+-SSL$",
    "firefox-beta-msi-latest-ssl": r"^Firefox-\d+\.0b\d+-msi-SSL$",
    "firefox-beta-msix-latest-ssl": r"^Firefox-\d+\.0b\d+-msix-SSL$",
    "firefox-beta-pkg-latest-ssl": r"^Firefox-\d+\.0b\d+-pkg-SSL$",
    "firefox-beta-langpack-latest-ssl": r"^Firefox-\d+\.0b\d+-langpack-SSL$",
    "firefox-stub": r"^Firefox-\d+\.\d+(\.\d+)?-stub$",
    "firefox-latest": r"^Firefox-\d+\.\d+(\.\d+)?$",
    "firefox-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?-SSL$",
    "firefox-msi-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?-msi-SSL$",
    "firefox-msix-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?-msix-SSL$",
    "firefox-langpack-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?-langpack-SSL$",
    "firefox-pkg-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?-pkg-SSL$",
    "firefox-esr-latest": r"^Firefox-\d+\.\d+(\.\d+)?esr$",
    "firefox-esr-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-SSL$",
    "firefox-esr-msi-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-msi-SSL$",
    "firefox-esr-msix-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-msix-SSL$",
    "firefox-esr-pkg-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-pkg-SSL$",
    "firefox-esr-langpack-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-langpack-SSL$",
    "firefox-esr-next-latest": r"^Firefox-\d+\.\d+(\.\d+)?esr$",
    "firefox-esr-next-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-SSL$",
    "firefox-esr-next-msi-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-msi-SSL$",
    "firefox-esr-next-msix-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-msix-SSL$",
    "firefox-esr-next-pkg-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-pkg-SSL$",
    "firefox-esr-next-langpack-latest-ssl": r"^Firefox-\d+\.\d+(\.\d+)?esr-langpack-SSL$",
    "firefox-esr115-latest": r"^Firefox-115\.\d+(\.\d+)?esr$",
    "firefox-esr115-latest-ssl": r"^Firefox-115\.\d+(\.\d+)?esr-SSL$",
    "firefox-esr115-msi-latest-ssl": r"^Firefox-115\.\d+(\.\d+)?esr-msi-SSL$",
    "firefox-esr115-msix-latest-ssl": r"^Firefox-115\.\d+(\.\d+)?esr-msix-SSL$",
    "firefox-esr115-pkg-latest-ssl": r"^Firefox-115\.\d+(\.\d+)?esr-pkg-SSL$",
    "firefox-esr115-langpack-latest-ssl": r"^Firefox-115\.\d+(\.\d+)?esr-langpack-SSL$",
}

PARTNER_ALIASES_REGEX = {
    r"^partner-firefox-beta-(.*)-latest$": r"^Firefox-\d+\.0b\d+-(.*)$",
    r"^partner-firefox-beta-(.*)-stub$": r"^Firefox-\d+\.0b\d+-(.*)-stub$",
    r"^partner-firefox-release-(.*)-latest$": r"^Firefox-\d+\.\d+(?:\.\d+)?-(.*)$",
    r"^partner-firefox-release-(.*)-stub$": r"^Firefox-\d+\.\d+(?:\.\d+)?-(.*)-stub$",
    r"^partner-firefox-esr-(.*)-latest$": r"^Firefox-\d+\.\d+(?:\.\d+)?esr-(.*)$",
    r"^partner-firefox-esr-(.*)-stub$": r"^Firefox-\d+\.\d+(?:\.\d+)?esr-(.*)-stub$",
}

PRODUCT_TO_DESTINATIONS_REGEXES = {
    "firefox-rc": (
        r"^(/firefox/candidates/.*?/build[0-9]+/(update/)?(?:linux-i686|linux-x86_64|linux-aarch64|mac|win32|win64(?:|-aarch64))/\:lang/(?:firefox|Firefox)"
        r".*\.(?:bz2|xz|dmg|exe|mar))$"
    ),
    "firefox": (
        r"^(/firefox/releases/.*?/(update/)?(?:linux-i686|linux-x86_64|linux-aarch64|mac|win32|win64(?:|-aarch64))/(?:(?:\:lang|multi)/(?:firefox|Firefox)"
        r".*\.(?:bz2|xz|dmg|exe|mar|msi|msix|pkg)|xpi/:lang.xpi))$"
    ),
    "devedition": (
        r"^(/devedition/releases/.*?/(update/)?(?:linux-i686|linux-x86_64|linux-aarch64|mac|win32|win64(?:|-aarch64))/(?:\:lang|multi)/(?:firefox|Firefox)"
        r".*\.(?:bz2|xz|dmg|exe|mar|msi|msix))$"
    ),
    "thunderbird": (
        r"^(/thunderbird/releases/.*?/(update/)?(?:linux-i686|linux-x86_64|mac|win32|win64(?:|-aarch64))/(?:\:lang|multi)/"
        r"(?:thunderbird|Thunderbird).*\.(?:bz2|xz|dmg|exe|mar|msi|msix))$"
    ),
}

_BOUNCER_PATH_REGEXES_PER_PRODUCT_DEFAULT = {
    "firefox-nightly-latest": (
        r"^(/firefox/nightly/latest-(mozilla-central|try)-l10n/firefox-\d+\.0a1\.:lang\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|linux-aarch64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
    "firefox-nightly-latest-ssl": (
        r"^(/firefox/nightly/latest-(mozilla-central|try)/firefox-\d+\.0a1\.en-US\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|linux-aarch64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
    "firefox-nightly-latest-l10n": (
        r"^(/firefox/nightly/latest-(mozilla-central|try)-l10n/firefox-\d+\.0a1\.:lang\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|linux-aarch64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
    "firefox-nightly-latest-l10n-ssl": (
        r"^(/firefox/nightly/latest-(mozilla-central|try)-l10n/firefox-\d+\.0a1\.:lang\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|linux-aarch64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
}

_BOUNCER_PATH_REGEXES_PER_ALTERNATIVE_PACKAGE_FORMAT = {
    **_BOUNCER_PATH_REGEXES_PER_PRODUCT_DEFAULT,
    "firefox-nightly-msi-latest-ssl": (
        r"^(/firefox/nightly/latest-(mozilla-central|try)/firefox-\d+\.0a1\.en-US\." r"(?:win32\.installer\.msi|win64(?:|-aarch64)\.installer\.msi))$"
    ),
    "firefox-nightly-msi-latest-l10n-ssl": (
        r"^(/firefox/nightly/latest-(mozilla-central|try)-l10n/firefox-\d+\.0a1\.:lang\." r"(?:win32\.installer\.msi|win64(?:|-aarch64)\.installer\.msi))$"
    ),
    "firefox-nightly-pkg-latest-ssl": (r"^(/firefox/nightly/latest-(mozilla-central|try)/firefox-\d+\.0a1\.en-US\." r"(?:mac\.pkg))$"),
    "firefox-nightly-pkg-latest-l10n-ssl": (r"^(/firefox/nightly/latest-(mozilla-central|try)-l10n/firefox-\d+\.0a1\.:lang\." r"(?:mac\.pkg))$"),
}

# msix should move up to _BOUNCER_PATH_REGEXES_PER_ALTERNATIVE_PACKAGE_FORMAT once it exists consistently
_BOUNCER_PATH_REGEXES_PER_ALTERNATIVE_PACKAGE_FORMAT_WITH_MSIX = {
    **_BOUNCER_PATH_REGEXES_PER_ALTERNATIVE_PACKAGE_FORMAT,
    "firefox-nightly-msix-latest-ssl": (r"^(/firefox/nightly/latest-(mozilla-central|try)/firefox-\d+\.0a1\.multi\." r"(?:(win32|win64)\.installer\.msix)$"),
}

_BOUNCER_PATH_REGEXES_PRODUCT_THUNDERBIRD = {
    "thunderbird-nightly-latest": (
        r"^(/thunderbird/nightly/latest-comm-central/thunderbird-\d+\.0a1\.en-US\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
    "thunderbird-nightly-latest-ssl": (
        r"^(/thunderbird/nightly/latest-comm-central/thunderbird-\d+\.0a1\.en-US\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
    "thunderbird-nightly-latest-l10n": (
        r"^(/thunderbird/nightly/latest-comm-central-l10n/thunderbird-\d+\.0a1\.:lang\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
    "thunderbird-nightly-latest-l10n-ssl": (
        r"^(/thunderbird/nightly/latest-comm-central-l10n/thunderbird-\d+\.0a1\.:lang\."
        r"(?:linux-i686\.tar\.(bz2|xz)|linux-x86_64\.tar\.(bz2|xz)|mac\.dmg|win32\.installer\.exe|win64\.installer\.exe|win64-aarch64\.installer\.exe))$"
    ),
    "thunderbird-nightly-msi-latest-ssl": (
        r"^(/thunderbird/nightly/latest-comm-central/thunderbird-\d+\.0a1\.en-US\." r"(?:win32\.installer\.msi|win64(?:|-aarch64)\.installer\.msi))$"
    ),
    "thunderbird-nightly-msi-latest-l10n-ssl": (
        r"^(/thunderbird/nightly/latest-comm-central-l10n/thunderbird-\d+\.0a1\.:lang\." r"(?:win32\.installer\.msi|win64(?:|-aarch64)\.installer\.msi))$"
    ),
    "thunderbird-nightly-pkg-latest-ssl": (r"^(/thunderbird/nightly/latest-comm-central/thunderbird-\d+\.0a1\.en-US\." r"(?:mac\.pkg))$"),
    "thunderbird-nightly-pkg-latest-l10n-ssl": (r"^(/thunderbird/nightly/latest-comm-central-l10n/thunderbird-\d+\.0a1\.:lang\." r"(?:mac\.pkg))$"),
}


BOUNCER_PATH_REGEXES_PER_PRODUCT = [
    _BOUNCER_PATH_REGEXES_PER_PRODUCT_DEFAULT,
    _BOUNCER_PATH_REGEXES_PER_ALTERNATIVE_PACKAGE_FORMAT,
    _BOUNCER_PATH_REGEXES_PER_ALTERNATIVE_PACKAGE_FORMAT_WITH_MSIX,
    _BOUNCER_PATH_REGEXES_PRODUCT_THUNDERBIRD,
]

# XXX A list of tuple is used because we care about the order:
# the firefox regex also matches the firefox-rc regex.
PRODUCT_TO_PRODUCT_ENTRY = [
    ("firefox-rc", r"^Firefox-.*build[0-9]+-.*$"),
    ("firefox", r"^Firefox-.*$"),
    ("devedition", r"^Devedition-.*$"),
    ("thunderbird", r"^Thunderbird-.*$"),
]

BOUNCER_LOCATION_PLATFORMS = ["linux", "linux64", "linux64-aarch64", "osx", "win", "win64", "android-x86", "android", "win64-aarch64", "linux64-aarch64"]

GO_BOUNCER_URL_TMPL = {
    "project:releng:bouncer:server:production": "https://download.mozilla.org/?product={}&print=yes",
    "project:comm:thunderbird:releng:bouncer:server:production": "https://download.mozilla.org/?product={}&print=yes",
    "project:releng:bouncer:server:staging": "https://dev.bouncer.nonprod.webservices.mozgcp.net/?product={}&print=yes",
    "project:comm:thunderbird:releng:bouncer:server:staging": "https://dev.bouncer.nonprod.webservices.mozgcp.net/?product={}&print=yes",
}

NIGHTLY_VERSION_REGEX = r"\d+\.\d+a1"
