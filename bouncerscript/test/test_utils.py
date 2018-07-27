import aiohttp
import json
import os
import pytest
import tempfile

from scriptworker.test import fake_session, fake_session_500
from scriptworker.exceptions import ScriptWorkerTaskException
import scriptworker.utils as sutils

import bouncerscript.utils as butils
from bouncerscript.utils import (
    api_update_alias, api_add_location, api_add_product,
    does_product_exist, api_call, _do_api_call, get_locations_paths,
    api_show_location, api_show_product
)
from bouncerscript.task import get_task_action, get_task_server
from bouncerscript.test import submission_context as context
from bouncerscript.test import (
    noop_async, fake_ClientError_throwing_session,
    fake_TimeoutError_throwing_session, load_json
)


assert context  # silence pyflakes
assert fake_session, fake_session_500  # silence flake8
assert noop_async  # silence flake8
assert fake_ClientError_throwing_session  # silence flake8
assert fake_TimeoutError_throwing_session  # silence flake8


def test_load_json_from_file():
    json_object = {'a_key': 'a_value'}

    with tempfile.TemporaryDirectory() as output_dir:
        output_file = os.path.join(output_dir, 'file.json')
        with open(output_file, 'w') as f:
            json.dump(json_object, f)

        assert load_json(output_file) == json_object


# api_call {{{1
@pytest.mark.parametrize("retry_config", ((
    None
), (
    {'retry_exceptions': aiohttp.ClientError}
)))
@pytest.mark.asyncio
async def test_api_call(context, mocker, retry_config):
    mocker.patch.object(butils, '_do_api_call', new=noop_async)
    mocker.patch.object(sutils, 'retry_async', new=noop_async)
    await api_call(context, 'dummy-route', {}, retry_config)


# _do_api_call {{{1
@pytest.mark.parametrize("data,credentials", ((
    {}, False
), (
    {'product': 'dummy'}, True
)))
def test_do_successful_api_call(context, mocker, event_loop, fake_session, data, credentials):
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_session

    if not credentials:
        del context.config["bouncer_config"][context.server]["username"]
        del context.config["bouncer_config"][context.server]["password"]

        with pytest.raises(KeyError):
            response = event_loop.run_until_complete(
                _do_api_call(context, 'dummy', data)
            )

        return

    response = event_loop.run_until_complete(
        _do_api_call(context, 'dummy', data)
    )

    assert response == '{}'


# _do_api_call {{{1
def test_do_failed_api_call(context, mocker, event_loop, fake_session_500):
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_session_500

    response = event_loop.run_until_complete(
        _do_api_call(context, 'dummy', {})
    )

    assert response == '{}'


# _do_api_call {{{1
def test_do_failed_with_ClientError_api_call(context, mocker, event_loop, fake_ClientError_throwing_session):
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_ClientError_throwing_session

    with pytest.raises(aiohttp.ClientError):
        event_loop.run_until_complete(
            _do_api_call(context, 'dummy', {})
        )


# _do_api_call {{{1
def test_do_failed_with_TimeoutError_api_call(context, mocker, event_loop, fake_TimeoutError_throwing_session):
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_TimeoutError_throwing_session

    with pytest.raises(aiohttp.ServerTimeoutError):
        event_loop.run_until_complete(
            _do_api_call(context, 'dummy', {})
        )


# does_product_exist {{{1
@pytest.mark.parametrize("product,response,expected", ((
    "fake-product",
    "<products/>",
    False,
), (
    "fake-product",
    "sd9fh398ghJKDFH@(*YFG@I#KJHWEF@(*G@",
    False,
), (
    "fake-product",
    "<product>fake-product</product>",
    True,
)))
@pytest.mark.asyncio
async def test_does_product_exist(context, mocker, product, response, expected):
    async def fake_api_call(context, product_name):
        return response

    mocker.patch.object(butils, 'api_show_product', new=fake_api_call)
    assert await does_product_exist(context, product) == expected


# api_add_product {{{1
@pytest.mark.parametrize("product,add_locales,ssl_only,expected", ((
    "fake-product",
    False,
    False, (
         "product_add/", {
             "product": "fake-product",
         },
    )
), (
    "fake-product",
    True,
    False, (
         "product_add/", {
             "product": "fake-product",
             "languages": ["en-US", "ro"],
         },
    )
), (
    "fake-product",
    False,
    True, (
         "product_add/", {
             "product": "fake-product",
             "ssl_only": "true",
         },
    )
), (
    "fake-product",
    True,
    True, (
         "product_add/", {
             "product": "fake-product",
             "languages": ["en-US", "ro"],
             "ssl_only": "true",
         },
    )
)))
@pytest.mark.asyncio
async def test_api_add_product(context, mocker, product, add_locales, ssl_only, expected):
    async def fake_api_call(context, route, data):
        return route, data

    mocker.patch.object(butils, 'api_call', new=fake_api_call)
    assert await api_add_product(context, product, add_locales, ssl_only) == expected


# api_add_location {{{1
@pytest.mark.parametrize("product,os,path,expected", ((
    "fake-product",
    "fake-os",
    "fake-path", (
         "location_add/", {
             "product": "fake-product",
             "os": "fake-os",
             "path": "fake-path",
         },
    )
),))
@pytest.mark.asyncio
async def test_api_add_location(context, mocker, product, os, path, expected):
    async def fake_api_call(context, route, data):
        return route, data

    mocker.patch.object(butils, 'api_call', new=fake_api_call)
    assert await api_add_location(context, product, os, path) == expected


# api_show_product {{{1
@pytest.mark.parametrize("product,provided,expected", ((
    "fake-Fennec-product",
    "<product>fake-product</product>",
    "<product>fake-product</product>",
), (
    "fake-Firefox-product",
    "<products/>",
    "<products/>",
)))
@pytest.mark.asyncio
async def test_api_show_product(context, mocker, product, provided, expected):
    async def fake_api_call(context, location, data):
        return provided

    mocker.patch.object(butils, 'api_call', new=fake_api_call)
    assert await api_show_product(context, product) == expected


# api_show_location {{{1
@pytest.mark.parametrize("product,expected", ((
    "fake-Fennec-product",
    ('<?xml version="1.0" encoding="utf-8"?><locations><product id="8692" '
     'name="Fennec-62.0b9"><location id="43593" os="android">/mobile/releases/'
     '62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk</location>'
     '<location id="43594" os="android-x86">/mobile/releases/62.0b9/android-x86/:'
     'lang/fennec-62.0b9.:lang.android-i386.apk</location></product></locations>'),
), (
    "fake-Firefox-product",
    ('<?xml version="1.0" encoding="utf-8"?><locations><product id="8692" '
     'name="Firefox-62.0b9"><location id="43593" os="mac">/firefox/releases/'
     '62.0b9/mac-api-16/:lang/firefox-62.0b9.:lang.mac-arm.dmg</location>'
     '<location id="43594" os="mac-x86">/firefox/releases/62.0b9/mac-x86/:'
     'lang/firefox-62.0b9.:lang.mac-i386.dmg</location></product></locations>'),
)))
@pytest.mark.asyncio
async def test_api_show_location(context, mocker, product, expected):
    async def fake_api_call(context, location, data):
        return expected

    mocker.patch.object(butils, 'api_call', new=fake_api_call)
    assert await api_show_location(context, product) == expected


# api_update_alias {{{1
@pytest.mark.parametrize("alias,product,expected", ((
    "fake-alias",
    "fake-product", (
         "create_update_alias", {
             "alias": "fake-alias",
             "related_product": "fake-product",
         },
    )
),))
@pytest.mark.asyncio
async def test_api_update_alias(context, mocker, alias, product, expected):
    async def fake_api_call(context, route, data):
        return route, data

    mocker.patch.object(butils, 'api_call', new=fake_api_call)
    assert await api_update_alias(context, alias, product) == expected


# get_locations_paths {{{1
@pytest.mark.parametrize("product,response,expected,raises", ((
    "fake-product",
    "<locations/>",
    [],
    False
), (
    "fake-product",
    # raises xml.parsers.expat.ExpatError
    "sd9fh398ghJKDFH@(*YFG@I#KJHWEF@(*G@",
    None,
    True
), (
    "fake-product",
    # raises UnicodeDecodeError
    b'<fran\xe7ais>Comment \xe7a va ? Tr\xe8s bien ?</fran\xe7ais>',
    None,
    True
), (
    "fake-product",
    # raises ValueError
    '<element xmlns:abc="http:abc.com/de f g/hi/j k"><abc:foo /></element>',
    None,
    True
), (
    "fake-product",
    ('<?xml version="1.0" encoding="utf-8"?><locations><product id="8692" '
     'name="Fennec-62.0b9"><location id="43593" os="android">/mobile/releases/'
     '62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk</location>'
     '<location id="43594" os="android-x86">/mobile/releases/62.0b9/android-x86/:'
     'lang/fennec-62.0b9.:lang.android-i386.apk</location></product></locations>'),
    [
        '/mobile/releases/62.0b9/android-api-16/:lang/fennec-62.0b9.:lang.android-arm.apk',
        '/mobile/releases/62.0b9/android-x86/:lang/fennec-62.0b9.:lang.android-i386.apk'
    ],
    False
), (
    "fake-product",
    ('<?xml version="1.0" encoding="utf-8"?><locations><product id="8696" '
     'name="Fennec-62.0b10"><location id="43610" os="android">/mobile/releases'
     '/62.0b10/android-api-16/:lang/fennec-62.0b10.:lang.android-arm.apk</'
     'location><location id="43611" os="android-x86">/mobile/releases/62.0b10/'
     'android-x86/:lang/fennec-62.0b10.:lang.android-i386.apk</location></'
     'product></locations>'),
    [
        '/mobile/releases/62.0b10/android-api-16/:lang/fennec-62.0b10.:lang.android-arm.apk',
        '/mobile/releases/62.0b10/android-x86/:lang/fennec-62.0b10.:lang.android-i386.apk'
    ],
    False,
)))
@pytest.mark.asyncio
async def test_get_locations_paths(context, mocker, product, response, expected,
                                   raises):
    async def fake_api_call(context, product):
        return response

    mocker.patch.object(butils, 'api_show_location', new=fake_api_call)
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            assert await get_locations_paths(context, product)
    else:
        assert await get_locations_paths(context, product) == expected
