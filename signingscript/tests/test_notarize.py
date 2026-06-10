import os
import shutil
from unittest import mock

import pytest
from conftest import TEST_DATA_DIR, noop_async, noop_sync

import signingscript.sign as sign
from signingscript.exceptions import SigningScriptError

# notarization {{{1


@pytest.mark.asyncio
async def test_notarize_single(mocker):
    retry_mock = mock.AsyncMock()
    mocker.patch.object(sign, "retry_async", retry_mock)
    await sign._notarize_single("/foo/bar", "/baz")
    retry_mock.assert_awaited()
    # cover no staple
    await sign._notarize_single("/foo/bar", "/baz", staple=False)


@pytest.mark.asyncio
async def test_notarize_pkg(mocker, context):
    mocker.patch.object(sign.shutil, "copy2", lambda *_: "/foo.pkg")
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/foo.pkg", "/baz"])
    mocker.patch.object(sign, "_notarize_single", noop_async)
    mocker.patch.object(sign, "_create_tarfile", noop_async)
    result = await sign._notarize_pkg(context, "/foo/bar", "/baz")
    assert result == "/foo.pkg"


@pytest.mark.asyncio
async def test_notarize_pkg_fail(mocker, context):
    mocker.patch.object(sign.shutil, "copy2", lambda *_: "/foo.pkg")
    mocker.patch.object(sign.os, "listdir", lambda *_: [])
    with pytest.raises(SigningScriptError):
        await sign._notarize_pkg(context, "/foo/bar", "/baz")


@pytest.mark.asyncio
async def test_notarize_all(mocker, context):
    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/foo.app"])
    mocker.patch.object(sign, "_notarize_single", noop_async)
    mocker.patch.object(sign, "_create_tarfile", noop_async)
    await sign._notarize_all(context, "/foo/bar", "/baz")


@pytest.mark.asyncio
async def test_notarize_all_fail(mocker, context):
    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign.os, "listdir", lambda *_: [])
    with pytest.raises(SigningScriptError):
        await sign._notarize_all(context, "/foo/bar", "/baz")


@pytest.mark.asyncio
async def test_apple_notarize(mocker, context):
    notarize_all = mock.AsyncMock()
    mocker.patch.object(sign, "_notarize_all", notarize_all)
    notarize_pkg = mock.AsyncMock()
    mocker.patch.object(sign, "_notarize_pkg", notarize_pkg)
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)

    await sign.apple_notarize(context, "/foo/bar.pkg")
    await sign.apple_notarize(context, "/foo/bar.tar.gz")
    notarize_pkg.assert_awaited_once()
    notarize_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_apple_notarize_fail_format(context):
    filename = "target.tar.gz"
    path = os.path.join(context.config["work_dir"], filename)
    shutil.copy2(os.path.join(TEST_DATA_DIR, filename), path)

    with pytest.raises(SigningScriptError, match=r"No supported files found"):
        await sign.apple_notarize(context, path)


@pytest.mark.asyncio
async def test_notarize_geckodriver(mocker, context):
    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign, "_create_zipfile", noop_async)
    mocker.patch.object(sign, "_notarize_single", noop_async)
    await sign._notarize_geckodriver(context, "/foo/geckodriver.tar.gz", "/foo")


@pytest.mark.asyncio
async def test_apple_notarize_geckodriver(mocker, context):
    notarize_geckodriver = mock.AsyncMock()
    mocker.patch.object(sign, "_notarize_geckodriver", notarize_geckodriver)
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)

    await sign.apple_notarize_geckodriver(context, "/foo/bar.pkg")
    notarize_geckodriver.assert_awaited_once()


@pytest.mark.asyncio
async def test_probe_staple_collect_failures(mocker):
    """Returns only the paths whose staple probe raised RCodesignError."""

    async def staple_side_effect(path):
        if path.endswith(".fail"):
            raise sign.RCodesignError("simulated probe failure")
        return None

    staple = mock.AsyncMock(side_effect=staple_side_effect)
    mocker.patch.object(sign, "rcodesign_staple", staple)

    result = await sign._probe_staple_collect_failures(["/a.ok", "/b.fail", "/c.ok"], {"attempts": 1})
    assert result == ["/b.fail"]
    assert staple.await_count == 3


@pytest.mark.asyncio
async def test_apple_notarize_stacked(mocker, context, monkeypatch):
    # First-run path: RUN_ID unset -> no .pkg probe, full notarize for every .pkg.
    monkeypatch.delenv("RUN_ID", raising=False)
    notarize_mock = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notarize", notarize_mock)
    wait = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notary_wait", wait)
    staple = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_staple", staple)

    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign, "_create_tarfile", noop_async)
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/foo.pkg", "/baz.app", "/foobar"])
    mocker.patch.object(sign.os, "walk", lambda *_: [("/", None, ["foo.pkg", "baz.app"])])
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)
    mocker.patch.object(sign.utils, "copy_to_dir", noop_sync)

    await sign.apple_notarize_stacked(
        context,
        {
            "/app.tar.gz": {"full_path": "/app.tar.gz", "formats": ["apple_notarize_stacked"]},
            "/app2.pkg": {"full_path": "/app2.pkg", "formats": ["apple_notarize_stacked"]},
        },
    )
    # Phase A notarizes/waits the 2 .pkgs; the 1 .app is transitively validated
    # by its parent .pkg, so only its Phase B staple probe runs (no notarize/wait).
    assert notarize_mock.await_count == 2
    assert wait.await_count == 2
    assert staple.await_count == 3


@pytest.mark.asyncio
async def test_apple_notarize_stacked_probe_fallback(mocker, context, monkeypatch):
    """.app staple probe fails -> fall back to full notarize/wait/staple."""
    monkeypatch.delenv("RUN_ID", raising=False)

    async def no_retry(func=None, args=(), kwargs=None, attempts=1, retry_exceptions=Exception, **_):
        kwargs = kwargs or {}
        return await func(*args, **kwargs)

    mocker.patch.object(sign, "retry_async", new=no_retry)

    notarize_mock = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notarize", notarize_mock)
    wait = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notary_wait", wait)

    app_probe_failures = {"remaining": 1}

    async def staple_side_effect(path):
        if path.endswith(".app") and app_probe_failures["remaining"] > 0:
            app_probe_failures["remaining"] -= 1
            raise sign.RCodesignError("simulated probe failure")
        return None

    staple = mock.AsyncMock(side_effect=staple_side_effect)
    mocker.patch.object(sign, "rcodesign_staple", staple)

    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign, "_create_tarfile", noop_async)
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/foo.pkg", "/baz.app", "/foobar"])
    mocker.patch.object(sign.os, "walk", lambda *_: [("/", None, ["foo.pkg", "baz.app"])])
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)
    mocker.patch.object(sign.utils, "copy_to_dir", noop_sync)

    await sign.apple_notarize_stacked(
        context,
        {
            "/app.tar.gz": {"full_path": "/app.tar.gz", "formats": ["apple_notarize_stacked"]},
            "/app2.pkg": {"full_path": "/app2.pkg", "formats": ["apple_notarize_stacked"]},
        },
    )
    # Phase A: 2 .pkgs notarized + waited + stapled.
    # Phase B: 1 probe attempt on the .app (raises).
    # Phase C: fallback notarize + wait + staple for that .app.
    assert notarize_mock.await_count == 3
    assert wait.await_count == 3
    assert staple.await_count == 4
    fallback_notarize = [c for c in notarize_mock.await_args_list if c.args[0].endswith(".app")]
    assert len(fallback_notarize) == 1


@pytest.mark.asyncio
async def test_apple_notarize_stacked_no_pkg_single_probe(mocker, context, monkeypatch):
    """When no .pkg is in the batch, .apps get a single-attempt probe, then Phase C."""
    monkeypatch.delenv("RUN_ID", raising=False)
    notarize_mock = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notarize", notarize_mock)
    wait = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notary_wait", wait)

    # Probe fails once; fallback staple in Phase C succeeds.
    app_probe_failures = {"remaining": 1}

    async def staple_side_effect(path):
        if path.endswith(".app") and app_probe_failures["remaining"] > 0:
            app_probe_failures["remaining"] -= 1
            raise sign.RCodesignError("simulated probe failure")
        return None

    staple = mock.AsyncMock(side_effect=staple_side_effect)
    mocker.patch.object(sign, "rcodesign_staple", staple)

    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign, "_create_tarfile", noop_async)
    # tar.gz extracts to a .app only (no .pkg alongside)
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/baz.app", "/foobar"])
    mocker.patch.object(sign.os, "walk", lambda *_: [("/", None, ["baz.app"])])
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)
    mocker.patch.object(sign.utils, "copy_to_dir", noop_sync)

    await sign.apple_notarize_stacked(
        context,
        {"/app.tar.gz": {"full_path": "/app.tar.gz", "formats": ["apple_notarize_stacked"]}},
    )
    # No .pkgs -> Phase A empty. Phase B probes once (fails, no retry).
    # Phase C notarizes/waits/staples the .app.
    assert notarize_mock.await_count == 1
    assert wait.await_count == 1
    assert staple.await_count == 2  # 1 probe (raises) + 1 Phase C staple (succeeds)


@pytest.mark.asyncio
async def test_apple_notarize_stacked_rerun_pkg_probe_succeeds(mocker, context, monkeypatch):
    """Rerun (RUN_ID != 0): .pkg staple probes succeed, so .pkgs are NOT re-notarized."""
    monkeypatch.setenv("RUN_ID", "1")
    notarize_mock = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notarize", notarize_mock)
    wait = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notary_wait", wait)
    staple = mock.AsyncMock()  # every probe succeeds
    mocker.patch.object(sign, "rcodesign_staple", staple)

    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign, "_create_tarfile", noop_async)
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/foo.pkg", "/baz.app", "/foobar"])
    mocker.patch.object(sign.os, "walk", lambda *_: [("/", None, ["foo.pkg", "baz.app"])])
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)
    mocker.patch.object(sign.utils, "copy_to_dir", noop_sync)

    await sign.apple_notarize_stacked(
        context,
        {
            "/app.tar.gz": {"full_path": "/app.tar.gz", "formats": ["apple_notarize_stacked"]},
            "/app2.pkg": {"full_path": "/app2.pkg", "formats": ["apple_notarize_stacked"]},
        },
    )
    # Phase A: 2 .pkg probes succeed -> no .pkg notarize/wait.
    # Phase B: 1 .app probe succeeds -> no Phase C.
    assert notarize_mock.await_count == 0
    assert wait.await_count == 0
    assert staple.await_count == 3  # 2 pkg probes + 1 app probe


@pytest.mark.asyncio
async def test_apple_notarize_stacked_rerun_pkg_probe_fails(mocker, context, monkeypatch):
    """Rerun (RUN_ID != 0): a .pkg probe fails -> that .pkg gets the full pipeline."""
    monkeypatch.setenv("RUN_ID", "1")
    notarize_mock = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notarize", notarize_mock)
    wait = mock.AsyncMock()
    mocker.patch.object(sign, "rcodesign_notary_wait", wait)

    # First .pkg probe fails; everything else (other .pkg probe, Phase A staple,
    # .app probe) succeeds.
    pkg_probe_failures = {"remaining": 1}

    async def staple_side_effect(path):
        if path.endswith(".pkg") and pkg_probe_failures["remaining"] > 0:
            pkg_probe_failures["remaining"] -= 1
            raise sign.RCodesignError("simulated pkg probe failure")
        return None

    staple = mock.AsyncMock(side_effect=staple_side_effect)
    mocker.patch.object(sign, "rcodesign_staple", staple)

    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign, "_create_tarfile", noop_async)
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/foo.pkg", "/baz.app", "/foobar"])
    mocker.patch.object(sign.os, "walk", lambda *_: [("/", None, ["foo.pkg", "baz.app"])])
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)
    mocker.patch.object(sign.utils, "copy_to_dir", noop_sync)

    await sign.apple_notarize_stacked(
        context,
        {
            "/app.tar.gz": {"full_path": "/app.tar.gz", "formats": ["apple_notarize_stacked"]},
            "/app2.pkg": {"full_path": "/app2.pkg", "formats": ["apple_notarize_stacked"]},
        },
    )
    # 1 of 2 .pkg probes fails -> that .pkg is notarized/waited/stapled.
    assert notarize_mock.await_count == 1
    assert wait.await_count == 1
    # staples: 2 pkg probes (1 fail + 1 ok) + 1 Phase A staple (failed pkg) + 1 app probe
    assert staple.await_count == 4
    notarized_pkgs = [c for c in notarize_mock.await_args_list if c.args[0].endswith(".pkg")]
    assert len(notarized_pkgs) == 1


@pytest.mark.asyncio
async def test_apple_notarize_stacked_unsupported(mocker, context):
    """Test unsupported file extensions"""

    mocker.patch.object(sign, "_extract_tarfile", noop_async)
    mocker.patch.object(sign.shutil, "rmtree", noop_sync)
    mocker.patch.object(sign.utils, "mkdir", noop_sync)
    mocker.patch.object(sign.utils, "copy_to_dir", noop_sync)

    # Returns unsupported file formats
    mocker.patch.object(sign.os, "listdir", lambda *_: ["/foo.aaa", "/baz.bbb", "/foobar"])

    with pytest.raises(SigningScriptError):
        # Main file is supported, contents uses the above os.listdir
        await sign.apple_notarize_stacked(
            context,
            {
                "/app.tar.gz": {"full_path": "/app.tar.gz", "formats": ["apple_notarize_stacked"]},
            },
        )

    with pytest.raises(SigningScriptError):
        # Main file extension is unsupported
        await sign.apple_notarize_stacked(
            context,
            {
                "/app.bbb": {"full_path": "/app.bbb", "formats": ["apple_notarize_stacked"]},
            },
        )
