
import mimetypes
import mock
import pytest
import sys

from beetmoverscript.script import setup_mimetypes, setup_config, put, retry_download
from beetmoverscript.test import get_fake_valid_config
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerRetryException
from scriptworker.test import event_loop, fake_session, fake_session_500

assert event_loop  # silence flake8
assert fake_session, fake_session_500  # silence flake8


def test_setup_mimetypes():
    non_default_types = [
        'https://foo.com/fake_artifact.bundle', 'http://www.bar.com/fake_checksum.beet'
    ]

    # before we add custom mimetypes
    assert ([mimetypes.guess_type(url)[0] for url in non_default_types] == [None, None])

    setup_mimetypes()

    # after we add custom mimetypes
    assert (sorted([mimetypes.guess_type(url)[0] for url in non_default_types]) ==
            ['application/octet-stream', 'text/plain'])


def test_invalid_args():
    args = ['only-one-arg']
    with mock.patch.object(sys, 'argv', args):
        with pytest.raises(SystemExit):
            setup_config(None)


def test_setup_config():
    expected_context = Context()
    expected_context.config = get_fake_valid_config()
    actual_context = setup_config("beetmoverscript/test/fake_config.json")
    assert expected_context.config == actual_context.config


def test_put_success(event_loop, fake_session):
    context = Context()
    context.config = get_fake_valid_config()
    context.session = fake_session
    response = event_loop.run_until_complete(
        put(context, url='https://foo.com/packages/fake.package', headers={},
            abs_filename='beetmoverscript/test/fake_artifact.json', session=fake_session)
    )
    assert response.status == 200
    assert response.resp == [b'asdf', b'asdf']
    assert response.content.url == "https://foo.com/packages/fake.package"
    assert response.content.method == "PUT"


def test_put_failure(event_loop, fake_session_500):
    context = Context()
    context.config = get_fake_valid_config()
    context.session = fake_session_500
    with pytest.raises(ScriptWorkerRetryException):
        event_loop.run_until_complete(
            put(context, url='https://foo.com/packages/fake.package', headers={},
                abs_filename='beetmoverscript/test/fake_artifact.json', session=fake_session_500)
        )


def test_download(event_loop):
    context = Context()
    context.config = get_fake_valid_config()
    context.session = fake_session
    url = 'https://fake.com'
    path = '/fake/path'

    async def fake_download(context, url, path, session):
        return context, url, path, session

    # just make sure retry_download ends up calling scriptworker's download_file and passes the
    # right args, kwargs
    with mock.patch('beetmoverscript.script.download_file', fake_download):
        result = event_loop.run_until_complete(
            retry_download(context, url, path)
        )
        assert result == (context, url, path, context.session)
