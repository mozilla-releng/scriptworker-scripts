try:
    from unittest.mock import create_autospec
except ImportError:
    from mock import create_autospec

from mozapkpublisher import googleplay


def craft_service_mock(monkeypatch_):
    edit_service_mock = create_autospec(googleplay.EditService)
    edit_service_mock.upload_apk.side_effect = [{'versionCode': str(i)} for i in range(1000)]
    monkeypatch_.setattr(googleplay, 'EditService', lambda _, __, ___, ____: edit_service_mock)
    return edit_service_mock
