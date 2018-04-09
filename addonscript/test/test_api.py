# import contextlib
# import json
import os
# import time
# import uuid

import aiohttp
import pytest
from aioresponses import aioresponses
# from jose import jws
# from jose.constants import ALGORITHMS
# from freezegun import freeze_time

from addonscript.test import tmpdir
from scriptworker.context import Context

import addonscript.api as api

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
                'jwt_secret': 'secret'
            },
        },
    }
    context.task = {
        'scopes': ['project:releng:addons.mozilla.org:server:dev']
    }
    return context


@pytest.fixture(scope='function')
async def fake_session(event_loop):
    async with aiohttp.ClientSession() as session:
        return session


@pytest.mark.asyncio
async def test_get_signed_xpi(fake_session, context, tmpdir):
    destination = os.path.join(tmpdir, 'langpack.xpi')
    download_path = 'https://addons.example.com/some/file+path'
    with aioresponses() as m:
        context.session = fake_session
        m.get(download_path, status=200, body=b'foobar')

        # py37 nullcontext would be better
        await api.get_signed_xpi(context, download_path, destination)
        with open(destination, 'rb') as f:
            contents = f.read()
        assert contents == b'foobar'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'expected_url,pk',
    (("api/v3/addons/langpack-en-GB@firefox.mozilla.org/versions/59.0buildid20180406102847/uploads/deadbeef/",
      'deadbeef'),
     ("api/v3/addons/langpack-en-GB@firefox.mozilla.org/versions/59.0buildid20180406102847/", None)),
)
async def test_get_upload_status(context, fake_session, expected_url, pk):
    context.locales = {}
    context.locales['en-GB'] = {
        'id': 'langpack-en-GB@firefox.mozilla.org',
        'version': '59.0buildid20180406102847',
    }
    mocked_url = "{}/{}".format('http://some-amo-it.url', expected_url)
    with aioresponses() as m:
        context.session = fake_session
        m.get(mocked_url, status=200, body='{"foo": "bar"}')

        resp = await api.get_upload_status(context, 'en-GB', pk)
        assert resp == {'foo': 'bar'}
