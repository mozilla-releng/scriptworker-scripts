import contextlib
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
from addonscript.exceptions import SignatureError, AMOConflictError

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
@pytest.mark.parametrize(
    'statuscode,raises',
    ((200, None),
     (203, None),
     (302, None),
     (401, aiohttp.client_exceptions.ClientResponseError),
     (503, aiohttp.client_exceptions.ClientResponseError),
     (409, AMOConflictError))
)
async def test_do_upload(fake_session, context, tmpdir, mocker, statuscode, raises):
    upload_file = '{}/test.xpi'.format(tmpdir)
    context.locales = {}
    context.locales['en-GB'] = {
        'id': 'langpack-en-GB@firefox.mozilla.org',
        'version': '59.0buildid20180406102847',
        'unsigned': upload_file,
    }
    with open(upload_file, 'wb') as f:
        f.write(b'foobar')
    expected_url = "api/v3/addons/{id}/versions/{version}/".format(
        id='langpack-en-GB@firefox.mozilla.org',
        version='59.0buildid20180406102847')
    mocked_url = "{}/{}".format('http://some-amo-it.url', expected_url)

    mocker.patch.object(api, 'get_channel', return_value='unlisted')

    with aioresponses() as m:
        context.session = fake_session
        m.put(mocked_url, status=statuscode, body='{"foo": "bar"}')

        raisectx = contextlib.suppress()
        if raises:
            raisectx = pytest.raises(raises)
        with raisectx:
            resp = await api.do_upload(context, 'en-GB')
            assert resp == {"foo": "bar"}


@pytest.mark.asyncio
async def test_get_signed_addon_url_success(context, mocker):
    status_json = {
        'files': [{
            'signed': True,
            'download_url': "https://some-download-url/foo",
        }]
    }

    async def new_upload_status(*args, **kwargs):
        return status_json

    mocker.patch.object(api, 'get_upload_status', new=new_upload_status)
    resp = await api.get_signed_addon_url(context, 'en-GB', 'deadbeef')
    assert resp == "https://some-download-url/foo"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'num_files,raises',
    ((0, True),
     (1, False),
     (2, True),
     (10, True))
)
async def test_get_signed_addon_url_files(context, mocker, num_files, raises):
    status_json = {'files': []}
    for unused in range(num_files):
        del unused  # Not used
        status_json['files'].append({
            'signed': True,
            'download_url': "https://some-download-url/foo",
        })

    async def new_upload_status(*args, **kwargs):
        return status_json

    mocker.patch.object(api, 'get_upload_status', new=new_upload_status)

    raisectx = contextlib.suppress()
    if raises:
        raisectx = pytest.raises(SignatureError)
    with raisectx as excinfo:
        resp = await api.get_signed_addon_url(context, 'en-GB', 'deadbeef')
        assert resp == "https://some-download-url/foo"
    if raises:
        assert "Expected 1 file" in str(excinfo.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'errors,raises',
    (([], False),
     (["deadbeef", "whimsycorn"], True),
     (["deadbeef"], True))
)
async def test_get_signed_addon_url_validation_errors(context, mocker, errors, raises):
    status_json = {
        'files': [{
            'signed': True,
            'download_url': "https://some-download-url/foo",
        }],
        'validation_results': {'errors': errors},
    }

    async def new_upload_status(*args, **kwargs):
        return status_json

    mocker.patch.object(api, 'get_upload_status', new=new_upload_status)

    raisectx = contextlib.suppress()
    if raises:
        raisectx = pytest.raises(SignatureError)
    with raisectx as excinfo:
        resp = await api.get_signed_addon_url(context, 'en-GB', 'deadbeef')
        assert resp == "https://some-download-url/foo"
    if raises:
        assert "Automated validation produced" in str(excinfo.value)
        for val in errors:
            assert val in str(excinfo.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'variant',
    ('signed', 'download')
)
async def test_get_signed_addon_url_other_errors(context, mocker, variant):
    status_json = {
        'files': [{
            'signed': True if variant != 'signed' else False,
        }],
    }
    if variant != "download":
        status_json['files'][0]['download_url'] = "https://some-download-url/foo"

    async def new_upload_status(*args, **kwargs):
        return status_json

    mocker.patch.object(api, 'get_upload_status', new=new_upload_status)

    raisectx = pytest.raises(SignatureError)
    with raisectx as excinfo:
        await api.get_signed_addon_url(context, 'en-GB', 'deadbeef')
    if variant == "signed":
        assert 'Expected XPI "signed" parameter' in str(excinfo.value)
    if variant == "download":
        assert 'Expected XPI "download_url" parameter' in str(excinfo.value)


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
