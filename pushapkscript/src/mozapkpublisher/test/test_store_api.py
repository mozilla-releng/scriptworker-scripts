from mozapkpublisher.common.store_api import build_apk_file_name


def test_build_apk_file_name():
    metadata = {
        "package_name": "org.mozilla.firefox",
        "architecture": "arm64-v8a",
        "version_name": "116.0",
    }
    assert build_apk_file_name(metadata) == "org.mozilla.firefox-arm64-v8a-116.0.apk"
