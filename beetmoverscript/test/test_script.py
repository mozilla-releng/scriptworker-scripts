
import mimetypes
import mock
import pytest
import sys

from beetmoverscript.script import setup_mimetypes, setup_config, put, retry_download, move_beets, \
    move_beet, async_main, main
from beetmoverscript.test import get_fake_valid_config, get_fake_valid_task
from beetmoverscript.utils import generate_candidates_manifest
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


# def test_upload_to_s3():
#     async def fake_aws_client(service, key, id):
#         s3_client = object()
#         s

def test_move_beets(event_loop):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    manifest = generate_candidates_manifest(context)

    expected_sources = [
        'https://queue.taskcluster.net/v1/task/VALID_TASK_ID/artifacts/public/build/target.package',
        'https://queue.taskcluster.net/v1/task/VALID_TASK_ID/artifacts/public/build/en-US/target.package'
    ]
    expected_destinations = [
        ('pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/fake-99.0a1.multi.fake.package',
         'pub/mobile/nightly/latest-mozilla-central-fake/fake-99.0a1.multi.fake.package'),
        ('pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.fake.package',
         'pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.fake.package')
    ]

    actual_sources = []
    actual_destinations = []
    async def fake_move_beet(context, source, destinations):
        actual_sources.append(source)
        actual_destinations.append(destinations)

    with mock.patch('beetmoverscript.script.move_beet', fake_move_beet):
        event_loop.run_until_complete(
            move_beets(context, manifest)
        )

    assert sorted(expected_sources) == sorted(actual_sources)
    assert sorted(expected_destinations) == sorted(actual_destinations)


def test_move_beet(event_loop):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()

    target_source = 'https://queue.taskcluster.net/v1/task/VALID_TASK_ID/artifacts/public/build/target.package'
    target_destinations = (
        'pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/fake-99.0a1.multi.fake.package',
        'pub/mobile/nightly/latest-mozilla-central-fake/fake-99.0a1.multi.fake.package'
    )
    expected_download_args = [
        'https://queue.taskcluster.net/v1/task/VALID_TASK_ID/artifacts/public/build/target.package',
        'beetmoverscript/test/test_work_dir/public/build/target.package'
    ]
    expected_upload_args = [
        ('pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/fake-99.0a1.multi.fake.package',
         'pub/mobile/nightly/latest-mozilla-central-fake/fake-99.0a1.multi.fake.package'),
        'beetmoverscript/test/test_work_dir/public/build/target.package'
    ]
    actual_download_args = []
    actual_upload_args = []

    async def fake_retry_download(context, url, path):
        actual_download_args.extend([url, path])
    async def fake_retry_upload(context, destinations, path):
        actual_upload_args.extend([destinations, path])

    with mock.patch('beetmoverscript.script.retry_download', fake_retry_download):
        with mock.patch('beetmoverscript.script.retry_upload', fake_retry_upload):
            event_loop.run_until_complete(
                move_beet(context, target_source, target_destinations)
            )

    assert sorted(expected_download_args) == sorted(actual_download_args)
    assert expected_upload_args == actual_upload_args


def test_async_main(event_loop):
    context = Context()
    context.config = get_fake_valid_config()

    async def fake_move_beets(context, manifest):
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

    with mock.patch('beetmoverscript.script.async_main', new=fake_async_main):
        main(name='__main__', config_path='beetmoverscript/test/fake_config.json')
