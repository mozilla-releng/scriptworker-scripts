import pytest
from mozapkpublisher.huawei_api import HuaweiAppGallery


@pytest.mark.asyncio
async def test_huawei_dry_run(responses_mock):
    # Having the `responses_mock` fixture in the test makes sure that this whole test doesn't try to contact any server
    credentials = {"key_id": "k", "sub_account": "s", "private_key": "x"}
    async with HuaweiAppGallery(credentials, dry_run=True) as huawei:
        await huawei.upload_apks('org.mozilla.firefox', [], None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dry_run,contact_server",
    (
        pytest.param(True, True, id="no_commit"),
        pytest.param(False, False, id="commit_but_do_not_contact_server"),
        pytest.param(True, False, id="neither"),
    ),
)
async def test_do_not_contact_server_stops_an_upload(monkeypatch, responses_mock, dry_run, contact_server):
    """`--do-not-contact-server` promises no request reaches the store, so it has to beat
    `--commit`. The `responses_mock` fixture fails the test if anything is sent."""
    from unittest.mock import MagicMock
    from mozapkpublisher import push_apk as push_apk_module

    monkeypatch.setattr(push_apk_module, 'extract_and_check_apks_metadata', lambda *a, **kw: {})
    monkeypatch.setattr(push_apk_module, 'load_credentials', lambda _: {"key_id": "k", "sub_account": "s", "private_key": "x"})
    gallery = MagicMock(wraps=HuaweiAppGallery)
    monkeypatch.setattr(push_apk_module, 'HuaweiAppGallery', gallery)

    await push_apk_module.push_apk(
        [], None, [], 'production', store='huawei', dry_run=dry_run, contact_server=contact_server,
        huawei_credentials='/dev/null',
    )

    assert gallery.call_args.kwargs['dry_run'] is True
