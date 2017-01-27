import mimetypes
import os

import mock
import pytest
import sys
from yarl import URL

from beetmoverscript.script import setup_mimetypes, setup_config, put, move_beets, \
    move_beet, async_main, main
from beetmoverscript.task import get_upstream_artifacts
from beetmoverscript.test import get_fake_valid_config, get_fake_valid_task, get_fake_balrog_props
from beetmoverscript.utils import generate_beetmover_manifest
from scriptworker.context import Context
from scriptworker.exceptions import (ScriptWorkerRetryException,
                                     ScriptWorkerTaskException)
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
        put(context, url=URL('https://foo.com/packages/fake.package'), headers={},
            abs_filename='beetmoverscript/test/fake_artifact.json', session=fake_session)
    )
    assert response.status == 200
    assert response.resp == [b'asdf', b'asdf']
    assert response.content.url == "https://foo.com/packages/fake.package"


def test_put_failure(event_loop, fake_session_500):
    context = Context()
    context.config = get_fake_valid_config()
    context.session = fake_session_500
    with pytest.raises(ScriptWorkerRetryException):
        event_loop.run_until_complete(
            put(context, url=URL('https://foo.com/packages/fake.package'), headers={},
                abs_filename='beetmoverscript/test/fake_artifact.json', session=fake_session_500)
        )


def test_move_beets(event_loop):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']
    context.artifacts_to_beetmove = get_upstream_artifacts(context)
    manifest = generate_beetmover_manifest(context.config, context.task, context.properties)

    expected_sources = [
        os.path.abspath(
            'beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.mozinfo.json'
        ),
        os.path.abspath(
            'beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.txt',
        ),
        os.path.abspath(
            'beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target_info.txt'
        ),
    ]
    expected_destinations = [
        ('pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_info.txt',
         'pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_info.txt'),
        ('pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.mozinfo.json',
         'pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.mozinfo.json'),
        ('pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt',
         'pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt'),
    ]

    actual_sources = []
    actual_destinations = []

    async def fake_move_beet(context, source, destinations, locale,
                             update_balrog_manifest, pretty_name):
        actual_sources.append(source)
        actual_destinations.append(destinations)

    with mock.patch('beetmoverscript.script.move_beet', fake_move_beet):
        event_loop.run_until_complete(
            move_beets(context, context.artifacts_to_beetmove, manifest)
        )

    assert sorted(expected_sources) == sorted(actual_sources)
    assert sorted(expected_destinations) == sorted(actual_destinations)


def test_move_beet(event_loop):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.checksums = dict()
    locale = "sample-locale"

    target_source = 'beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.txt'
    pretty_name = 'fake-99.0a1.en-US.target.txt'
    target_destinations = (
        'pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt',
        'pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt'
    )
    expected_upload_args = [
        ('pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt',
         'pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt'),
        'beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.txt'
    ]
    actual_upload_args = []

    async def fake_retry_upload(context, destinations, path):
        actual_upload_args.extend([destinations, path])

    with mock.patch('beetmoverscript.script.retry_upload', fake_retry_upload):
        event_loop.run_until_complete(
            move_beet(context, target_source, target_destinations, locale,
                      update_balrog_manifest=False, pretty_name=pretty_name)
        )

    assert expected_upload_args == actual_upload_args


def test_async_main(event_loop):
    context = Context()
    context.config = get_fake_valid_config()

    async def fake_move_beets(context, artifacts_to_beetmove, manifest):
        pass

    with mock.patch('beetmoverscript.script.move_beets', new=fake_move_beets):
        event_loop.run_until_complete(
            async_main(context)
        )


def test_main(event_loop, fake_session):
    context = Context()
    context.config = get_fake_valid_config()

    async def fake_async_main(context):
        pass

    async def fake_async_main_with_exception(context):
        raise ScriptWorkerTaskException("This is wrong, the answer is 42")

    with mock.patch('beetmoverscript.script.async_main', new=fake_async_main):
        main(name='__main__', config_path='beetmoverscript/test/fake_config.json')

    with mock.patch('beetmoverscript.script.async_main', new=fake_async_main_with_exception):
        try:
            main(name='__main__', config_path='beetmoverscript/test/fake_config.json')
        except SystemExit as exc:
            assert exc.code == 1
