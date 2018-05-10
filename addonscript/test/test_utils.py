import contextlib
import json
import os
import time
import uuid

import aiohttp
import pytest
from aioresponses import aioresponses
from freezegun import freeze_time
from jose import jws
from jose.constants import ALGORITHMS
from scriptworker.context import Context

import addonscript.utils as utils
from addonscript.test import tmpdir

assert tmpdir  # silence flake8

# helper constants, fixtures, functions {{{1
# EXAMPLE_CONFIG = os.path.join(BASE_DIR, 'config_example.json')


@pytest.fixture(scope='function')
def context():
    context = Context()
    context.config = {
        'amo_instances': {
            'project:releng:addons.mozilla.org:server:dev': {
                'amo_server': 'http://some-amo-it.url',
                'jwt_user': 'test-user',
                'jwt_secret': 'secret',
            },
        },
    }
    context.task = {
        'scopes': ['project:releng:addons.mozilla.org:server:dev'],
    }
    return context


@pytest.fixture(scope='function')
@freeze_time('2018-01-19 12:59:59')
def payload():
    _iat = int(time.time())
    payload = {
        'iss': 'test-user',
        'jti': str(uuid.uuid4()),
        'iat': _iat,
        'exp': _iat + 60*4,
    }
    return payload


@pytest.fixture(scope='function')
async def fake_session(event_loop):
    async with aiohttp.ClientSession() as session:
        return session


@freeze_time('2018-01-19 12:59:59')
def test_generate_JWT(mocker, context, payload):
    mocker.patch.object(utils, 'uuid4', side_effect=lambda: payload['jti'])
    token = utils.generate_JWT(context)
    verify_bytes = jws.verify(token, 'secret', ALGORITHMS.HS256)
    assert json.loads(verify_bytes.decode('UTF-8')) == payload


@pytest.mark.asyncio
@pytest.mark.parametrize('http_code', (200, 203, 302, 404, 502))
async def test_amo_get_raises_status(fake_session, context, http_code):
    with aioresponses() as m:
        context.session = fake_session
        m.get('https://addons.example.com/some/api', status=http_code, body='{"foo": "bar"}')

        # py37 nullcontext would be better
        raises = contextlib.suppress()
        if (http_code >= 400):
            raises = pytest.raises(aiohttp.client_exceptions.ClientResponseError)
        with raises:
            resp = await utils.amo_get(context, 'https://addons.example.com/some/api')
            assert resp == {'foo': 'bar'}


@pytest.mark.asyncio
async def test_amo_get_header(fake_session, mocker, context):
    headers = {}

    with aioresponses() as m:
        context.session = fake_session
        m.get('https://addons.example.com/some/api', status=200, body="{}")

        def header_test(*args, **kwargs):
            headers.update(kwargs['headers'])
            mocker.stopall()
            return context.session.get(*args, **kwargs)

        mocker.patch.object(context.session, 'get', new=header_test)

        await utils.amo_get(context, 'https://addons.example.com/some/api')
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith("JWT ")


@pytest.mark.asyncio
async def test_amo_download_header(fake_session, mocker, context, tmpdir):
    headers = {}

    with aioresponses() as m:
        context.session = fake_session
        m.get('https://addons.example.com/some/api', status=200, body=b"deadbeef")

        def header_test(*args, **kwargs):
            headers.update(kwargs['headers'])
            mocker.stopall()
            return context.session.get(*args, **kwargs)

        mocker.patch.object(context.session, 'get', new=header_test)

        with open(os.path.join(tmpdir, 'test_file.bin'), 'wb') as f:
            await utils.amo_download(
                context, 'https://addons.example.com/some/api', file=f)
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith("JWT ")


@pytest.mark.asyncio
@pytest.mark.parametrize('http_code', (200, 203, 302, 404, 502))
async def test_amo_download_raises_status(fake_session, context, tmpdir, http_code):
    testfile = os.path.join(tmpdir, 'test_file.bin')
    with aioresponses() as m:
        context.session = fake_session
        m.get('https://addons.example.com/some/api', status=http_code, body=b"deadbeef")

        # py37 nullcontext would be better
        raises = contextlib.suppress()
        expect_empty_file = False
        if (http_code >= 400):
            raises = pytest.raises(aiohttp.client_exceptions.ClientResponseError)
            expect_empty_file = True
        with raises:
            with open(testfile, 'wb') as f:
                await utils.amo_download(
                    context, 'https://addons.example.com/some/api', file=f)
        assert os.path.isfile(testfile)
        if expect_empty_file:
            os.stat(testfile).st_size == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('http_code', (200, 203, 302, 404, 502))
async def test_amo_put_raises_status(fake_session, context, http_code):
    with aioresponses() as m:
        context.session = fake_session
        m.put('https://addons.example.com/some/api', status=http_code, body='{"foo": "bar"}')

        # py37 nullcontext would be better
        raises = contextlib.suppress()
        if (http_code >= 400):
            raises = pytest.raises(aiohttp.client_exceptions.ClientResponseError)
        with raises:
            resp = await utils.amo_put(context, 'https://addons.example.com/some/api', data={})
            assert resp == {'foo': 'bar'}


@pytest.mark.asyncio
async def test_amo_put_header(fake_session, mocker, context):
    headers = {}

    with aioresponses() as m:
        context.session = fake_session
        m.put('https://addons.example.com/some/api', status=200, body="{}")

        def header_test(*args, **kwargs):
            headers.update(kwargs['headers'])
            mocker.stopall()
            return context.session.put(*args, **kwargs)

        mocker.patch.object(context.session, 'put', new=header_test)

        await utils.amo_put(context, 'https://addons.example.com/some/api', data={})
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith("JWT ")


@pytest.mark.parametrize(
    'host,path', (
        ('https://addons.example.com', 'some/api'),
        ('https://addons.mozilla.org', 'what/api/is/this/'),
    ),
)
def test_get_api_url(host, path, context):
    context.config['amo_instances']['project:releng:addons.mozilla.org:server:dev']['amo_server'] = host
    url = utils.get_api_url(context, path)
    assert url.startswith(host)
    assert url.endswith(path)


def test_get_api_formatted(context):
    host = 'https://addons.example.com'
    context.config['amo_instances']['project:releng:addons.mozilla.org:server:dev']['amo_server'] = host
    url = utils.get_api_url(context, 'some/formatted/{api}/path', api='magic_api')
    assert url.startswith(host)
    assert url.endswith('some/formatted/magic_api/path')
