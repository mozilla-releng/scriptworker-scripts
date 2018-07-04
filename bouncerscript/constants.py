ALIASES_REGEXES = {
    'thunderbird-beta-latest': '^Thunderbird-\d+\.0b\d+$',
    'thunderbird-beta-latest-ssl': '^Thunderbird-\d+\.0b\d+-SSL$',
    'thunderbird-next-latest': '^Thunderbird-\d+\.\d+(\.\d+)?$',
    'thunderbird-next-latest-ssl': '^Thunderbird-\d+\.\d+(\.\d+)?-SSL$',
    'thunderbird-latest': '^Thunderbird-\d+\.\d+(\.\d+)?$',
    'thunderbird-latest-ssl': '^Thunderbird-\d+\.\d+(\.\d+)?-SSL$',
    'fennec-beta-latest': '^Fennec-\d+\.0b\d+$',
    'fennec-latest': '^Fennec-\d+\.\d+(\.\d+)?$',
    'firefox-devedition-stub': '^Devedition-\d+\.0b\d+-stub$',
    'firefox-devedition-latest': '^Devedition-\d+\.0b\d+$',
    'firefox-devedition-latest-ssl': '^Devedition-\d+\.0b\d+-SSL$',
    'firefox-beta-stub': '^Firefox-\d+\.0b\d+-stub$',
    'firefox-beta-latest': '^Firefox-\d+\.0b\d+$',
    'firefox-beta-latest-ssl': '^Firefox-\d+\.0b\d+-SSL$',
    'firefox-stub': '^Firefox-\d+\.\d+(\.\d+)?-stub$',
    'firefox-latest': '^Firefox-\d+\.\d+(\.\d+)?$',
    'firefox-latest-ssl': '^Firefox-\d+\.\d+(\.\d+)?-SSL$',
    'firefox-esr-latest': '^Firefox-\d+\.\d+(\.\d+)?esr$',
    'firefox-esr-latest-ssl': '^Firefox-\d+\.\d+(\.\d+)?esr-SSL$',
    'firefox-esr-next-latest': '^Firefox-\d+\.\d+(\.\d+)?esr$',
    'firefox-esr-next-latest-ssl': '^Firefox-\d+\.\d+(\.\d+)?esr-SSL$',
    'firefox-sha1': '^Firefox-\d+\.\d+(\.\d+)?esr-sha1$',
    'firefox-sha1-ssl': '^Firefox-\d+\.\d+(\.\d+)?esr-sha1$',
}


PRODUCT_TO_DESTINATIONS_REGEXES = {
    'fennec': '^(/mobile/releases/.*?/(?:android-api-16|android-x86)/\:lang/fennec-.*\:lang\.(?:android-arm|android-i386)\.apk)$',
    'firefox': '^(/firefox/releases/.*?/(update/)?(?:linux-i686|linux-x86_64|mac|win32|win64)/\:lang/(?:firefox|Firefox).*\.(?:bz2|dmg|exe|mar))$',
    'devedition': '^(/devedition/releases/.*?/(update/)?(?:linux-i686|linux-x86_64|mac|win32|win64)/\:lang/(?:firefox|Firefox).*\.(?:bz2|dmg|exe|mar))$',
    'thunderbird': '^(/thunderbird/releases/.*?/(update/)?(?:linux-i686|linux-x86_64|mac|win32|win64)/\:lang/(?:thunderbird|Thunderbird).*\.(?:bz2|dmg|exe|mar))$',
}

PRODUCT_TO_PRODUCT_ENTRY = {
    'fennec': r'^Fennec-.*$',
    'firefox': r'^Firefox-.*$',
    'devedition': r'^Devedition-.*$',
    'thunderbird': r'^Thunderbird-.*$',
}
