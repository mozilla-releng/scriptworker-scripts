import itertools

import mock
import pytest
from scriptworker.exceptions import ScriptWorkerTaskException, TaskVerificationError

import bouncerscript.script as bscript
from bouncerscript.script import async_main, bouncer_aliases, bouncer_locations, bouncer_submission, main

from . import counted, noop_async, noop_sync, raise_sync, return_empty_list_async, return_false_async, return_true_async, return_true_sync, toggled_boolean_async


# main {{{1
def test_main(submission_context):
    async def fake_async_main_with_exception(context):
        raise ScriptWorkerTaskException("This is wrong, the answer is 42")

    with mock.patch("bouncerscript.script.async_main", new=noop_async):
        main(config_path="tests/fake_config.json")

    with mock.patch("bouncerscript.script.async_main", new=fake_async_main_with_exception):
        try:
            main(config_path="tests/fake_config.json")
        except SystemExit as exc:
            assert exc.code == 1


# bouncer_submission {{{1
@pytest.mark.asyncio
async def test_bouncer_submission(submission_context, mocker):
    mocker.patch.object(bscript, "does_product_exist", new=toggled_boolean_async)
    mocker.patch.object(bscript, "api_add_product", new=noop_async)
    mocker.patch.object(bscript, "api_add_location", new=noop_async)
    mocker.patch.object(bscript, "get_locations_info", new=return_empty_list_async)
    mocker.patch.object(bscript, "does_location_path_exist", new=toggled_boolean_async)
    mocker.patch.object(bscript, "check_locations_match", new=raise_sync)
    mocker.patch.object(bscript, "check_path_matches_destination", new=noop_sync)

    with pytest.raises(ScriptWorkerTaskException):
        await bouncer_submission(submission_context)

    mocker.patch.object(bscript, "check_locations_match", new=noop_sync)
    await bouncer_submission(submission_context)

    mocker.patch.object(bscript, "check_path_matches_destination", new=raise_sync)
    with pytest.raises(ScriptWorkerTaskException):
        await bouncer_submission(submission_context)

    mocker.patch.object(bscript, "does_product_exist", new=return_false_async)
    with pytest.raises(ScriptWorkerTaskException):
        await bouncer_submission(submission_context)


@pytest.mark.asyncio
async def test_bouncer_submission_creates_locations_even_when_product_already_exists(submission_context, mocker):
    api_add_location_call_counter = itertools.count()

    async def mock_api_add_location(*args, **kwargs):
        next(api_add_location_call_counter)

    mocker.patch.object(bscript, "api_add_location", new=mock_api_add_location)
    mocker.patch.object(bscript, "does_product_exist", new=return_true_async)
    mocker.patch.object(bscript, "api_add_product", new=noop_async)
    mocker.patch.object(bscript, "get_locations_info", new=return_empty_list_async)
    mocker.patch.object(bscript, "does_location_path_exist", new=return_false_async)
    mocker.patch.object(bscript, "check_locations_match", new=noop_sync)
    mocker.patch.object(bscript, "check_path_matches_destination", new=noop_sync)
    await bouncer_submission(submission_context)
    assert next(api_add_location_call_counter) == 10


@pytest.mark.asyncio
async def test_bouncer_submission_creates_locations_even_some_exists(submission_context, mocker):
    api_add_location_call_counter = itertools.count()

    async def mock_api_add_location(*args, **kwargs):
        next(api_add_location_call_counter)

    mocker.patch.object(bscript, "api_add_location", new=mock_api_add_location)
    mocker.patch.object(bscript, "does_product_exist", new=return_true_async)
    mocker.patch.object(bscript, "api_add_product", new=noop_async)
    mocker.patch.object(bscript, "get_locations_info", new=return_empty_list_async)
    mocker.patch.object(bscript, "does_location_path_exist", new=toggled_boolean_async)
    mocker.patch.object(bscript, "check_locations_match", new=noop_sync)
    mocker.patch.object(bscript, "check_path_matches_destination", new=noop_sync)
    await bouncer_submission(submission_context)
    assert next(api_add_location_call_counter) == 5


# bouncer_aliases {{{1
@pytest.mark.asyncio
async def test_bouncer_aliases(aliases_context, mocker):
    mocker.patch.object(bscript, "api_update_alias", new=noop_async)
    mocker.patch.object(bscript, "check_aliases_match", new=noop_async)
    await bouncer_aliases(aliases_context)


@pytest.mark.parametrize(
    "info,updated_info,raises",
    (
        (
            [
                {"os": "win", "id": "47767", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win32.installer.exe"},
                {"os": "linux", "id": "47764", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win64.installer.exe"},
                {"os": "osx", "id": "47766", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.mac.dmg"},
                {"os": "linux64", "id": "47765", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.linux-x86_64.tar.bz2"},
                {"os": "win64", "id": "47768", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.linux-i686.tar.bz2"},
            ],
            [],
            False,
        ),
        (
            [
                {"os": "win", "id": "47767", "path": "/firefox/nightly/latest-mozilla-central/firefox-65.0a1.en-US.win32.installer.exe"},
                {"os": "linux", "id": "47764", "path": "/firefox/nightly/latest-mozilla-central/firefox-65.0a1.en-US.win64.installer.exe"},
            ],
            [],
            True,
        ),
        (
            [
                {"os": "win", "id": "47767", "path": "/firefox/nightly/latest-mozilla-central/firefox-62.0a1.en-US.win32.installer.exe"},
                {"os": "linux", "id": "47764", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win64.installer.exe"},
            ],
            [],
            True,
        ),
        (
            [
                {"os": "win", "id": "47767", "path": "/firefox/nightly/latest-mozilla-central/firefox-64.0a1.en-US.win32.installer.exe"},
                {"os": "linux", "id": "47764", "path": "/firefox/nightly/latest-mozilla-central/firefox-64.0a1.en-US.win64.installer.exe"},
            ],
            [],
            True,
        ),
        (
            [
                {"os": "win", "id": "47767", "path": "/firefox/nightly/latest-mozilla-central/firefox-62.0a1.en-US.win32.installer.exe"},
                {"os": "linux", "id": "47764", "path": "/firefox/nightly/latest-mozilla-central/firefox-62.0a1.en-US.win64.installer.exe"},
            ],
            [
                {"os": "win", "id": "47767", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win32.installer.exe"},
                {"os": "linux", "id": "47764", "path": "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win64.installer.exe"},
            ],
            False,
        ),
    ),
)
# bouncer_locations {{{1
@pytest.mark.asyncio
async def test_bouncer_locations(locations_context, mocker, info, updated_info, raises):
    async def fake_get_locations_info(*args, **kwargs):
        return info

    @counted
    async def toggled_get_locations_info(*args, **kwargs):
        if toggled_get_locations_info.calls & 1:
            return info
        else:
            return updated_info

    locations_context.task["payload"]["bouncer_products"] = ["firefox-nightly-latest"]
    locations_context.task["payload"]["product"] = "firefox"
    mocker.patch.object(bscript, "check_product_names_match_nightly_locations", new=noop_sync)
    mocker.patch.object(bscript, "check_version_matches_nightly_regex", new=noop_sync)
    mocker.patch.object(bscript, "does_product_exist", new=return_false_async)

    with pytest.raises(ScriptWorkerTaskException):
        await bouncer_locations(locations_context)

    mocker.patch.object(bscript, "does_product_exist", new=return_true_async)
    mocker.patch.object(bscript, "get_locations_info", new=fake_get_locations_info)
    mocker.patch.object(bscript, "check_location_path_matches_destination", new=noop_sync)
    mocker.patch.object(bscript, "api_modify_location", new=noop_async)

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            await bouncer_locations(locations_context)
    else:
        if updated_info != []:
            mock = mocker.MagicMock()
            mock.side_effect = toggled_get_locations_info
            mocker.patch.object(bscript, "get_locations_info", new=mock)
        await bouncer_locations(locations_context)


# async_main {{{1
@pytest.mark.asyncio
async def test_async_main(submission_context, mocker):
    mocker.patch.object(bscript, "bouncer_submission", new=noop_async)
    mocker.patch.object(bscript, "does_product_exist", new=noop_async)
    mocker.patch.object(bscript, "api_add_product", new=noop_async)
    mocker.patch.object(bscript, "api_add_location", new=noop_async)
    mocker.patch.object(bscript, "get_locations_info", new=noop_async)
    mocker.patch.object(bscript, "check_locations_match", new=return_true_sync)

    with pytest.raises(ScriptWorkerTaskException):
        await async_main(submission_context)

    mocker.patch.object(bscript, "action_map", new={})
    with pytest.raises(TaskVerificationError):
        await async_main(submission_context)
