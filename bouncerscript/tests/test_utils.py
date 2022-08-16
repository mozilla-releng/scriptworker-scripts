import json
import os
import tempfile

import aiohttp
import pytest
import scriptworker.utils as sutils
from scriptworker.exceptions import ScriptWorkerTaskException

import bouncerscript.utils as butils
from bouncerscript.task import get_task_action, get_task_server
from bouncerscript.utils import (
    _do_api_call,
    api_add_location,
    api_add_product,
    api_call,
    api_modify_location,
    api_show_location,
    api_show_product,
    api_update_alias,
    does_product_exist,
    get_locations_info,
    get_nightly_version,
    get_version_bumped_path,
)

from . import load_json, noop_async


def test_load_json_from_file():
    json_object = {"a_key": "a_value"}

    with tempfile.TemporaryDirectory() as output_dir:
        output_file = os.path.join(output_dir, "file.json")
        with open(output_file, "w") as f:
            json.dump(json_object, f)

        assert load_json(output_file) == json_object


# api_call {{{1
@pytest.mark.parametrize("retry_config", ((None), ({"retry_exceptions": aiohttp.ClientError})))
@pytest.mark.asyncio
async def test_api_call(submission_context, mocker, retry_config):
    mocker.patch.object(butils, "_do_api_call", new=noop_async)
    mocker.patch.object(sutils, "retry_async", new=noop_async)
    await api_call(submission_context, "dummy-route", {}, retry_config)


# _do_api_call {{{1
@pytest.mark.parametrize("data,credentials", (({}, False), ({"product": "dummy"}, True)))
def test_do_successful_api_call(submission_context, mocker, event_loop, fake_session, data, credentials):
    context = submission_context
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_session

    if not credentials:
        del context.config["bouncer_config"][context.server]["username"]
        del context.config["bouncer_config"][context.server]["password"]

        with pytest.raises(KeyError):
            response = event_loop.run_until_complete(_do_api_call(context, "dummy", data))

        return

    response = event_loop.run_until_complete(_do_api_call(context, "dummy", data))

    assert response == "{}"


# _do_api_call {{{1
def test_do_failed_api_call(submission_context, mocker, event_loop, fake_session_500):
    context = submission_context
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_session_500

    response = event_loop.run_until_complete(_do_api_call(context, "dummy", {}))

    assert response == "{}"


# _do_api_call {{{1
def test_do_failed_with_ClientError_api_call(submission_context, mocker, event_loop, fake_ClientError_throwing_session):
    context = submission_context
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_ClientError_throwing_session

    with pytest.raises(aiohttp.ClientError):
        event_loop.run_until_complete(_do_api_call(context, "dummy", {}))


# _do_api_call {{{1
def test_do_failed_with_TimeoutError_api_call(submission_context, mocker, event_loop, fake_TimeoutError_throwing_session):
    context = submission_context
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_TimeoutError_throwing_session

    with pytest.raises(aiohttp.ServerTimeoutError):
        event_loop.run_until_complete(_do_api_call(context, "dummy", {}))


# does_product_exist {{{1
@pytest.mark.parametrize(
    "product,response,expected",
    (("fake-product", "<products/>", False), ("fake-product", "sd9fh398ghJKDFH@(*YFG@I#KJHWEF@(*G@", False), ("fake-product", "<product>fake-product</product>", True)),
)
@pytest.mark.asyncio
async def test_does_product_exist(submission_context, mocker, product, response, expected):
    context = submission_context

    async def fake_api_call(context, product_name):
        return response

    mocker.patch.object(butils, "api_show_product", new=fake_api_call)
    assert await does_product_exist(context, product) == expected


# api_add_product {{{1
@pytest.mark.parametrize(
    "product,add_locales,ssl_only,expected",
    (
        ("fake-product", False, False, ("product_add/", {"product": "fake-product"})),
        ("fake-product", True, False, ("product_add/", {"product": "fake-product", "languages": ["en-US", "ro"]})),
        ("fake-product", False, True, ("product_add/", {"product": "fake-product", "ssl_only": "true"})),
        ("fake-product", True, True, ("product_add/", {"product": "fake-product", "languages": ["en-US", "ro"], "ssl_only": "true"})),
    ),
)
@pytest.mark.asyncio
async def test_api_add_product(submission_context, mocker, product, add_locales, ssl_only, expected):
    context = submission_context

    async def fake_api_call(context, route, data):
        return route, data

    mocker.patch.object(butils, "api_call", new=fake_api_call)
    assert await api_add_product(context, product, add_locales, ssl_only) == expected


# api_add_location {{{1
@pytest.mark.parametrize(
    "product,os,path,expected", (("fake-product", "fake-os", "fake-path", ("location_add/", {"product": "fake-product", "os": "fake-os", "path": "fake-path"})),)
)
@pytest.mark.asyncio
async def test_api_add_location(submission_context, mocker, product, os, path, expected):
    context = submission_context

    async def fake_api_call(context, route, data):
        return route, data

    mocker.patch.object(butils, "api_call", new=fake_api_call)
    assert await api_add_location(context, product, os, path) == expected


# api_modify_location {{{1
@pytest.mark.parametrize(
    "product,os,path,expected", (("fake-product", "fake-os", "fake-path", ("location_modify/", {"product": "fake-product", "os": "fake-os", "path": "fake-path"})),)
)
@pytest.mark.asyncio
async def test_api_modify_location(submission_context, mocker, product, os, path, expected):
    context = submission_context

    async def fake_api_call(context, route, data):
        return route, data

    mocker.patch.object(butils, "api_call", new=fake_api_call)
    assert await api_modify_location(context, product, os, path) == expected


# api_show_product {{{1
@pytest.mark.parametrize(
    "product,provided,expected",
    (("fake-Fennec-product", "<product>fake-product</product>", "<product>fake-product</product>"), ("fake-Firefox-product", "<products/>", "<products/>")),
)
@pytest.mark.asyncio
async def test_api_show_product(submission_context, mocker, product, provided, expected):
    context = submission_context

    async def fake_api_call(context, location, data):
        return provided

    mocker.patch.object(butils, "api_call", new=fake_api_call)
    assert await api_show_product(context, product) == expected


# api_show_location {{{1
@pytest.mark.parametrize(
    "product,expected",
    (
        (
            "fake-Fennec-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="8692" '
                'name="Fennec-62.0b9"><location id="43593" os="android">/mobile/releases/'
                "62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk</location>"
                '<location id="43594" os="android-x86">/mobile/releases/62.0b9/android-x86/:'
                "lang/fennec-62.0b9.:lang.android-i386.apk</location></product></locations>"
            ),
        ),
        (
            "fake-Firefox-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="8692" '
                'name="Firefox-62.0b9"><location id="43593" os="mac">/firefox/releases/'
                "62.0b9/mac-api-16/:lang/firefox-62.0b9.:lang.mac-arm.dmg</location>"
                '<location id="43594" os="mac-x86">/firefox/releases/62.0b9/mac-x86/:'
                "lang/firefox-62.0b9.:lang.mac-i386.dmg</location></product></locations>"
            ),
        ),
    ),
)
@pytest.mark.asyncio
async def test_api_show_location(submission_context, mocker, product, expected):
    context = submission_context

    async def fake_api_call(context, location, data):
        return expected

    mocker.patch.object(butils, "api_call", new=fake_api_call)
    assert await api_show_location(context, product) == expected


# api_update_alias {{{1
@pytest.mark.parametrize("alias,product,expected", (("fake-alias", "fake-product", ("create_update_alias", {"alias": "fake-alias", "related_product": "fake-product"})),))
@pytest.mark.asyncio
async def test_api_update_alias(submission_context, mocker, alias, product, expected):
    context = submission_context

    async def fake_api_call(context, route, data):
        return route, data

    mocker.patch.object(butils, "api_call", new=fake_api_call)
    assert await api_update_alias(context, alias, product) == expected

    [
        {"os": "", "id": "", "path": "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk"},
        {"os": "", "id": "", "path": "/mobile/releases/62.0b9/android-x86/:lang/fennec-62.0b9.:lang.android-i386.apk"},
    ]


# does_location_path_exist {{{1
@pytest.mark.parametrize(
    "platform, path, returned_locations, expected",
    (
        (
            "android",
            "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk",
            [
                {"os": "android", "id": "1234", "path": "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk"},
                {"os": "android-x86", "id": "5678", "path": "/mobile/releases/62.0b9/android-x86/:lang/fennec-62.0b9.:lang.android-i386.apk"},
            ],
            True,
        ),
        (
            "not-android",
            "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk",
            [
                {"os": "android", "id": "1234", "path": "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk"},
                {"os": "android-x86", "id": "5678", "path": "/mobile/releases/62.0b9/android-x86/:lang/fennec-62.0b9.:lang.android-i386.apk"},
            ],
            False,
        ),
        (
            "android",
            "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk",
            [{"os": "android", "id": "1234", "path": "/mobile/releases/62.0b9/android-x86/:lang/fennec-62.0b9.:lang.android-i386.apk"}],
            False,
        ),
        ("android", "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk", [], False),
    ),
)
@pytest.mark.asyncio
async def test_does_location_path_exist(submission_context, mocker, platform, path, returned_locations, expected):
    context = submission_context

    async def patch_get_locations_paths(*args, **kwargs):
        return returned_locations

    mocker.patch.object(butils, "get_locations_info", new=patch_get_locations_paths)
    assert await butils.does_location_path_exist(context, "fake-product", platform, path) == expected


# get_locations_info {{{1
@pytest.mark.parametrize(
    "product,response,expected,raises",
    (
        ("fake-product", "<locations/>", [], False),
        (
            "fake-product",
            # raises xml.parsers.expat.ExpatError
            "sd9fh398ghJKDFH@(*YFG@I#KJHWEF@(*G@",
            None,
            True,
        ),
        (
            "fake-product",
            # raises UnicodeDecodeError
            b"<fran\xe7ais>Comment \xe7a va ? Tr\xe8s bien ?</fran\xe7ais>",
            None,
            True,
        ),
        (
            "fake-product",
            # raises ValueError
            '<element xmlns:abc="http:abc.com/de f g/hi/j k"><abc:foo /></element>',
            None,
            True,
        ),
        (
            "fake-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="8692" '
                'name="Fennec-62.0b9"><location id="43593" os="android">/mobile/releases/'
                "62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk</location>"
                '<location id="43594" os="android-x86">/mobile/releases/62.0b9/android-x86/:'
                "lang/fennec-62.0b9.:lang.android-i386.apk</location></product></locations>"
            ),
            [
                {"os": "android", "id": "43593", "path": "/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk"},
                {"os": "android-x86", "id": "43594", "path": "/mobile/releases/62.0b9/android-x86/:lang/fennec-62.0b9.:lang.android-i386.apk"},
            ],
            False,
        ),
        (
            "fake-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="8696" '
                'name="Fennec-62.0b10"><location id="43610" os="android">/mobile/releases'
                "/62.0b10/android-api-16/:lang/fennec-62.0b10.:lang.android-arm.apk</"
                'location><location id="43611" os="android-x86">/mobile/releases/62.0b10/'
                "android-x86/:lang/fennec-62.0b10.:lang.android-i386.apk</location></"
                "product></locations>"
            ),
            [
                {"os": "android", "id": "43610", "path": "/mobile/releases/62.0b10/android-api-16/:lang/fennec-62.0b10.:lang.android-arm.apk"},
                {"os": "android-x86", "id": "43611", "path": "/mobile/releases/62.0b10/android-x86/:lang/fennec-62.0b10.:lang.android-i386.apk"},
            ],
            False,
        ),
        (
            "fake-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="9551" '
                'name="Firefox-62.0b16-stub"><location id="47774" os="win">/firefox/'
                "releases/62.0b16/win32/:lang/Firefox%20Installer.exe</location><location "
                'id="47775" os="win64">/firefox/releases/62.0b16/win32/:lang/Firefox%20'
                "Installer.exe</location></product></locations>"
            ),
            [
                {"os": "win", "id": "47774", "path": "/firefox/releases/62.0b16/win32/:lang/Firefox%20Installer.exe"},
                {"os": "win64", "id": "47775", "path": "/firefox/releases/62.0b16/win32/:lang/Firefox%20Installer.exe"},
            ],
            False,
        ),
        (
            "fake-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="9549" '
                'name="Firefox-62.0b16-Partial-62.0b15"><location id="47767" os="win">'
                "/firefox/releases/62.0b16/update/win32/:lang/firefox-62.0b15-62.0b16."
                'partial.mar</location><location id="47764" os="linux">/firefox/releases/'
                "62.0b16/update/linux-i686/:lang/firefox-62.0b15-62.0b16.partial.mar</"
                'location><location id="47766" os="osx">/firefox/releases/62.0b16/update'
                "/mac/:lang/firefox-62.0b15-62.0b16.partial.mar</location><location "
                'id="47765" os="linux64">/firefox/releases/62.0b16/update/linux-x86_64/:'
                'lang/firefox-62.0b15-62.0b16.partial.mar</location><location id="47768" '
                'os="win64">/firefox/releases/62.0b16/update/win64/:lang/firefox-62.0b15-'
                "62.0b16.partial.mar</location></product></locations>"
            ),
            [
                {"os": "win", "id": "47767", "path": "/firefox/releases/62.0b16/update/win32/:lang/firefox-62.0b15-62.0b16.partial.mar"},
                {"os": "linux", "id": "47764", "path": "/firefox/releases/62.0b16/update/linux-i686/:lang/firefox-62.0b15-62.0b16.partial.mar"},
                {"os": "osx", "id": "47766", "path": "/firefox/releases/62.0b16/update/mac/:lang/firefox-62.0b15-62.0b16.partial.mar"},
                {"os": "linux64", "id": "47765", "path": "/firefox/releases/62.0b16/update/linux-x86_64/:lang/firefox-62.0b15-62.0b16.partial.mar"},
                {"os": "win64", "id": "47768", "path": "/firefox/releases/62.0b16/update/win64/:lang/firefox-62.0b15-62.0b16.partial.mar"},
            ],
            False,
        ),
        (
            "fake-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="9538" '
                'name="Devedition-62.0b16"><location id="47715" os="win">/devedition/'
                "releases/62.0b16/win32/:lang/Firefox%20Setup%2062.0b16.exe</location>"
                '<location id="47712" os="linux">/devedition/releases/62.0b16/linux-'
                'i686/:lang/firefox-62.0b16.tar.bz2</location><location id="47714" '
                'os="osx">/devedition/releases/62.0b16/mac/:lang/Firefox%2062.0b16.dmg'
                '</location><location id="47713" os="linux64">/devedition/releases/62.'
                "0b16/linux-x86_64/:lang/firefox-62.0b16.tar.bz2</location><location "
                'id="47716" os="win64">/devedition/releases/62.0b16/win64/:lang/'
                "Firefox%20Setup%2062.0b16.exe</location></product></locations>"
            ),
            [
                {"os": "win", "id": "47715", "path": "/devedition/releases/62.0b16/win32/:lang/Firefox%20Setup%2062.0b16.exe"},
                {"os": "linux", "id": "47712", "path": "/devedition/releases/62.0b16/linux-i686/:lang/firefox-62.0b16.tar.bz2"},
                {"os": "osx", "id": "47714", "path": "/devedition/releases/62.0b16/mac/:lang/Firefox%2062.0b16.dmg"},
                {"os": "linux64", "id": "47713", "path": "/devedition/releases/62.0b16/linux-x86_64/:lang/firefox-62.0b16.tar.bz2"},
                {"os": "win64", "id": "47716", "path": "/devedition/releases/62.0b16/win64/:lang/Firefox%20Setup%2062.0b16.exe"},
            ],
            False,
        ),
        (
            "fake-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="2005" '
                'name="firefox-nightly-latest"><location id="9379" os="win">/firefox/nightly/'
                "latest-mozilla-central-l10n/firefox-66.0a1.:lang.win32.installer.exe"
                '</location><location id="23647" os="linux">/firefox/nightly/latest-'
                "mozilla-central-l10n/firefox-66.0a1.:lang.linux-i686.tar.bz2</location>"
                '<location id="23645" os="osx">/firefox/nightly/latest-mozilla-central-'
                'l10n/firefox-66.0a1.:lang.mac.dmg</location><location id="23646" '
                'os="linux64">/firefox/nightly/latest-mozilla-central-l10n/firefox-66.'
                '0a1.:lang.linux-x86_64.tar.bz2</location><location id="20140" os="win64"'
                ">/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win64."
                'installer.exe</location><location id="51281" os="win64-aarch64">/firefox'
                "/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win64-aarch64."
                "installer.exe</location></product></locations>"
            ),
            [
                {"os": "win", "id": "9379", "path": "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win32.installer.exe"},
                {"os": "linux", "id": "23647", "path": "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.linux-i686.tar.bz2"},
                {"os": "osx", "id": "23645", "path": "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.mac.dmg"},
                {"os": "linux64", "id": "23646", "path": "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.linux-x86_64.tar.bz2"},
                {"os": "win64", "id": "20140", "path": "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win64.installer.exe"},
                {"os": "win64-aarch64", "id": "51281", "path": "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win64-aarch64.installer.exe"},
            ],
            False,
        ),
        (
            "fake-product",
            (
                '<?xml version="1.0" encoding="utf-8"?><locations><product id="8696" '
                'name="Fennec-62.0b10"><location id="43610" os="android-corrupt-platform">/mobile/releases'
                "/62.0b10/android-api-16/:lang/fennec-62.0b10.:lang.android-arm.apk</"
                'location><location id="43611" os="android-x86">/mobile/releases/62.0b10/'
                "android-x86/:lang/fennec-62.0b10.:lang.android-i386.apk</location></"
                "product></locations>"
            ),
            [],
            True,
        ),
    ),
)
@pytest.mark.asyncio
async def test_get_locations_info(submission_context, mocker, product, response, expected, raises):
    context = submission_context

    async def fake_api_call(context, product):
        return response

    mocker.patch.object(butils, "api_show_location", new=fake_api_call)
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            await get_locations_info(context, product)
    else:
        assert await get_locations_info(context, product) == expected


# get_nightly_version {{{1
@pytest.mark.parametrize(
    "product,path,expected,raises",
    (
        ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.bz2", "63.0a1", False),
        ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exe", "63.0a1", False),
        ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-x86_64.tar.bz2", "63.0a1", False),
        ("firefox-nightly-latest-ssl", "  /firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.linux-x86_64.tar.bz2", "63.0a1", False),
        ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win32.installer.exe", "63.0a1", False),
        ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win64.installer.exe", "63.0a1", False),
        ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0.1.:lang.win64.installer.exe", "", True),
        ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0.:lang.win64.installer.exe", "", True),
        ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0b1.:lang.win64.installer.exe", "", True),
        ("fennec-nightly-latest", "/mobile/nightly/latest-mozilla-esr68-android-api-16/fennec-68.1a1.:lang.android-arm.apk", "68.1a1", False),
        ("fennec-nightly-latest", "/mobile/nightly/latest-mozilla-esr68-android-x86/fennec-68.1a1.:lang.android-i386.apk", "68.1a1", False),
        ("fennec-nightly-latest", "/mobile/nightly/latest-mozilla-esr68-android-x86/fennec-68.1b1.:lang.android-i386.apk", "", True),
        ("fennec-nightly-latest", "/mobile/nightly/latest-mozilla-esr68-android-x86/fennec-68.1.0.:lang.android-i386.apk", "", True),
        ("fennec-nightly-latest", "/mobile/nightly/latest-mozilla-esr68-android-x86/fennec-68a1.:lang.android-i386.apk", "", True),
        ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0a1.:lang.linux-i686.tar.bz2", "63.0a1", False),
        ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0a1.:lang.win32.installer.exe", "63.0a1", False),
        ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0a1.:lang.linux-x86_64.tar.bz2", "63.0a1", False),
        ("thunderbird-nightly-latest-ssl", "  /thunderbird/nightly/latest-comm-central/thunderbird-63.0a1.en-US.linux-x86_64.tar.bz2", "63.0a1", False),
        ("thunderbird-nightly-latest-ssl", "/thunderbird/nightly/latest-comm-central/thunderbird-63.0a1.en-US.win32.installer.exe", "63.0a1", False),
        ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0a1.:lang.win64.installer.exe", "63.0a1", False),
        ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0.1.:lang.win64.installer.exe", "", True),
        ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0.:lang.win64.installer.exe", "", True),
        ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0b1.:lang.win64.installer.exe", "", True),
    ),
)
def test_get_nightly_version(product, path, expected, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_nightly_version(product, path)
    else:
        get_nightly_version(product, path) == expected


# get_version_bumped_path {{{1
@pytest.mark.parametrize(
    "path,current_version,next_version,expected",
    (
        (
            "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.bz2",
            "63.0a1",
            "64.0a1",
            "/firefox/nightly/latest-mozilla-central-l10n/firefox-64.0a1.:lang.linux-i686.tar.bz2",
        ),
        (
            "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.bz2",
            "63.0a1",
            "64.0b1",
            "/firefox/nightly/latest-mozilla-central-l10n/firefox-64.0b1.:lang.linux-i686.tar.bz2",
        ),
        (
            "/mobile/nightly/latest-mozilla-esr68-android-x86/fennec-68.1a1.:lang.android-i386.apk",
            "68.1a1",
            "68.2a1",
            "/mobile/nightly/latest-mozilla-esr68-android-x86/fennec-68.2a1.:lang.android-i386.apk",
        ),
        (
            "/mobile/nightly/latest-mozilla-esr68-android-api-16/fennec-68.1a1.:lang.android-arm.apk",
            "68.1a1",
            "68.2a1",
            "/mobile/nightly/latest-mozilla-esr68-android-api-16/fennec-68.2a1.:lang.android-arm.apk",
        ),
        (
            "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-100.0a1.:lang.linux-i686.tar.bz2",
            "100.0a1",
            "101.0a1",
            "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-101.0a1.:lang.linux-i686.tar.bz2",
        ),
        (
            "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-100.0a1.:lang.linux-i686.tar.bz2",
            "100.0a1",
            "101.0b1",
            "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-101.0b1.:lang.linux-i686.tar.bz2",
        ),
    ),
)
def test_get_version_bumped_path(path, current_version, next_version, expected):
    assert get_version_bumped_path(path, current_version, next_version) == expected
