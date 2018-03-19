import aiohttp
import json
import os
import pytest
import tempfile

import bouncerscript.utils as butils
from bouncerscript.utils import (
    api_update_alias, api_add_location, api_add_product,
    does_product_exists, api_call, _do_api_call
)
from bouncerscript.task import get_task_action, get_task_server
from bouncerscript.test import submission_context as context
from bouncerscript.test import (
    noop_async, fake_ClientError_throwing_session,
    fake_TimeoutError_throwing_session, load_json
)
from scriptworker.test import event_loop, fake_session, fake_session_500
import scriptworker.utils as sutils


assert context  # silence pyflakes
assert fake_session, fake_session_500  # silence flake8
assert event_loop  # silence flake8
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
    context.session.close()


# _do_api_call {{{1
def test_do_failed_api_call(context, mocker, event_loop, fake_session_500):
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_session_500

    response = event_loop.run_until_complete(
        _do_api_call(context, 'dummy', {})
    )

    assert response == '{}'
    context.session.close()


# _do_api_call {{{1
def test_do_failed_with_ClientError_api_call(context, mocker, event_loop, fake_ClientError_throwing_session):
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_ClientError_throwing_session

    with pytest.raises(aiohttp.ClientError):
        event_loop.run_until_complete(
            _do_api_call(context, 'dummy', {})
        )

    context.session.close()


# _do_api_call {{{1
def test_do_failed_with_TimeoutError_api_call(context, mocker, event_loop, fake_TimeoutError_throwing_session):
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)
    context.session = fake_TimeoutError_throwing_session

    with pytest.raises(aiohttp.ServerTimeoutError):
        event_loop.run_until_complete(
            _do_api_call(context, 'dummy', {})
        )

    context.session.close()


# does_product_exists {{{1
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
async def test_does_product_exists(context, mocker, product, response, expected):
    async def fake_api_call(context, route, data):
        return response

    mocker.patch.object(butils, 'api_call', new=fake_api_call)
    assert await does_product_exists(context, product) == expected


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
