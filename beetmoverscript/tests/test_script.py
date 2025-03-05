import logging
import mimetypes
import os
import shutil

import boto3
import mock
import pytest
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerRetryException, ScriptWorkerTaskException
from yarl import URL

import beetmoverscript.script
from beetmoverscript.constants import PARTNER_REPACK_REGEXES
from beetmoverscript.script import (
    async_main,
    copy_beets,
    enrich_balrog_manifest,
    get_destination_for_partner_repack_path,
    list_bucket_objects,
    main,
    move_beet,
    move_beets,
    move_partner_beets,
    push_to_partner,
    push_to_releases_s3,
    put,
    sanity_check_partner_path,
    setup_mimetypes,
)
from beetmoverscript.task import get_release_props, get_upstream_artifacts
from beetmoverscript.utils import generate_beetmover_manifest, is_promotion_action

from . import get_fake_valid_config, get_fake_valid_task, get_test_jinja_env, noop_async, noop_sync


# push_to_partner {{{1
@pytest.mark.asyncio
async def test_push_to_partner(context, mocker):
    mocker.patch("beetmoverscript.script.move_partner_beets", new=noop_async)
    mocker.patch("beetmoverscript.utils.JINJA_ENV", get_test_jinja_env())
    await push_to_partner(context)


# push_to_releases_s3 {{{1
@pytest.mark.parametrize(
    "candidates_keys,releases_keys,exception_type",
    (({"foo.zip": "x", "foo.exe": "y"}, {}, None), ({"foo.zip": "x", "foo.exe": "y"}, {"asdf": 1}, None), ({}, {"asdf": 1}, ScriptWorkerTaskException)),
)
@pytest.mark.asyncio
async def test_push_to_releases_s3(context, mocker, candidates_keys, releases_keys, exception_type):
    context.task = {"payload": {"product": "devedition", "build_number": 33, "version": "99.0b44"}}

    objects = [candidates_keys, releases_keys]

    def check(_, _2, r):
        assert r == releases_keys

    def fake_list(*args):
        return objects.pop(0)

    mocker.patch.object(boto3, "resource")
    mocker.patch.object(beetmoverscript.script, "list_bucket_objects", new=fake_list)
    mocker.patch.object(beetmoverscript.script, "copy_beets", new=check)

    if exception_type is not None:
        with pytest.raises(exception_type):
            await push_to_releases_s3(context)
    else:
        await push_to_releases_s3(context)


# copy_beets {{{1
@pytest.mark.parametrize("releases_keys,raises", (({}, False), ({"to2": "from2_md5"}, False), ({"to1": "to1_md5"}, True)))
def test_copy_beets(context, mocker, releases_keys, raises):
    called_with = []

    def fake_copy_object(**kwargs):
        called_with.append(kwargs)

    boto_client = mock.MagicMock()
    boto_client.copy_object = fake_copy_object
    mocker.patch.object(boto3, "client", return_value=boto_client)
    context.artifacts_to_beetmove = {"from1": "to1", "from2": "to2"}
    candidates_keys = {"from1": "from1_md5", "from2": "from2_md5"}
    context.bucket_name = "this-is-a-fake-bucket"
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            copy_beets(context, candidates_keys, releases_keys)
    else:
        copy_beets(context, candidates_keys, releases_keys)
        a = {"Bucket": context.bucket_name, "CopySource": {"Bucket": context.bucket_name, "Key": "from1"}, "Key": "to1"}
        b = {"Bucket": context.bucket_name, "CopySource": {"Bucket": context.bucket_name, "Key": "from2"}, "Key": "to2"}
        if releases_keys:
            expected = [[a]]
        else:
            # Allow for different sorting
            expected = [[a, b], [b, a]]
        assert called_with in expected


# list_bucket_objects {{{1
def test_list_bucket_objects():
    bucket = mock.MagicMock()
    s3_resource = mock.MagicMock()

    def fake_bucket(_):
        return bucket

    def fake_filter(**kwargs):
        one = mock.MagicMock()
        two = mock.MagicMock()
        one.key = "one"
        one.e_tag = "asdf-x"
        two.key = "two"
        two.e_tag = "foo-bar"
        return [one, two]

    s3_resource.Bucket = fake_bucket
    bucket.objects.filter = fake_filter

    assert list_bucket_objects(mock.MagicMock(), s3_resource, None) == {"one": "asdf", "two": "foo"}


# setup_mimetypes {{{1
@pytest.mark.parametrize(
    "url,expected_type",
    [
        ("https://foo.com/fake_artifact.bundle", "application/octet-stream"),
        ("http://www.bar.com/fake_checksum.beet", "text/plain"),
        ("http://www.baz.com/fake.msix", "application/msix"),
        ("geckoview-nightly-omni-x86-94.0.20210928095433.module", "application/json"),
        ("geckoview-nightly-omni-x86-94.0.20210928095433.pom.sha512", "text/plain"),
    ],
)
def test_setup_mimetypes(url, expected_type):
    # ensure we start with mimetypes in its initial state
    mimetypes.init()
    # before we add custom mimetypes
    assert mimetypes.guess_type(url)[0] is None

    setup_mimetypes()

    # after we add custom mimetypes
    assert mimetypes.guess_type(url)[0] == expected_type


# put {{{1
@pytest.mark.asyncio
async def test_put_success(fake_session):
    context = Context()
    context.config = get_fake_valid_config()
    context.session = fake_session
    response = await put(context, url=URL("https://foo.com/packages/fake.package"), headers={}, abs_filename="tests/fake_artifact.json", session=fake_session)
    assert response.status == 200
    assert response.resp == [b"asdf", b"asdf"]


@pytest.mark.asyncio
async def test_put_failure(fake_session_500):
    context = Context()
    context.config = get_fake_valid_config()
    context.session = fake_session_500
    with pytest.raises(ScriptWorkerRetryException):
        await put(context, url=URL("https://foo.com/packages/fake.package"), headers={}, abs_filename="tests/fake_artifact.json", session=fake_session_500)


# enrich_balrog_manifest {{{1
@pytest.mark.parametrize("branch,action", (("mozilla-central", "push-to-nightly"), ("try", "push-to-nightly"), ("mozilla-beta", "push-to-releases")))
def test_enrich_balrog_manifest(context, branch, action):
    context.task["payload"]["build_number"] = 33
    context.task["payload"]["version"] = "99.0b44"
    context.action = action
    context.release_props["branch"] = branch

    expected_data = {
        "appName": context.release_props["appName"],
        "appVersion": context.release_props["appVersion"],
        "branch": context.release_props["branch"],
        "buildid": context.release_props["buildid"],
        "extVersion": context.release_props["appVersion"],
        "hashType": context.release_props["hashType"],
        "locale": "sample-locale",
        "platform": context.release_props["stage_platform"],
        "url_replacements": [],
    }
    if branch != "try":
        expected_data["url_replacements"] = [["http://archive.mozilla.org/pub", "http://download.cdn.mozilla.net/pub"]]
    if action != "push-to-nightly":
        expected_data["tc_release"] = True
        expected_data["build_number"] = 33
        expected_data["version"] = "99.0b44"
    else:
        expected_data["tc_nightly"] = True

    data = enrich_balrog_manifest(context, "sample-locale")
    assert data == expected_data


# retry_upload {{{1
@pytest.mark.asyncio
async def test_retry_upload(context, mocker):
    mocker.patch.object(beetmoverscript.script, "upload_to_s3", new=noop_async)
    mocker.patch.object(beetmoverscript.script, "upload_to_gcs", new=noop_async)
    await beetmoverscript.script.retry_upload(context, ["a", "b"], "c")


# upload_to_s3 {{{1
@pytest.mark.asyncio
async def test_upload_to_s3(context, mocker):
    setup_mimetypes()
    context.release_props["appName"] = "fake"
    mocker.patch.object(beetmoverscript.script, "retry_async", new=noop_async)
    mocker.patch.object(beetmoverscript.script, "boto3")
    await beetmoverscript.script.upload_to_s3(context, "foo", "bar")


@pytest.mark.asyncio
async def test_upload_to_s3_raises(context, mocker):
    setup_mimetypes()
    context.release_props["appName"] = "fake"
    mocker.patch.object(beetmoverscript.script, "retry_async", new=noop_async)
    mocker.patch.object(beetmoverscript.script, "boto3")
    with pytest.raises(ScriptWorkerTaskException):
        await beetmoverscript.script.upload_to_s3(context, "foo", "mime.invalid")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fail_on_unknown_mime_type",
    (
        pytest.param(
            True,
            id="fail_on_unknown_mime_type",
        ),
        pytest.param(
            False,
            id="dont_fail_on_unknown_mime_type",
        ),
    ),
)
async def test_upload_to_s3_fail_on_missing_mime_type(context, mocker, fail_on_unknown_mime_type):
    setup_mimetypes()
    context.release_props["appName"] = "fake"
    mocked_retry_async = mocker.patch.object(beetmoverscript.script, "retry_async")
    mocker.patch.object(beetmoverscript.script, "boto3")
    if fail_on_unknown_mime_type:
        with pytest.raises(ScriptWorkerTaskException):
            await beetmoverscript.script.upload_to_s3(context, "foo", "mime.invalid", fail_on_unknown_mime_type)
    else:
        await beetmoverscript.script.upload_to_s3(context, "foo", "mime.invalid", fail_on_unknown_mime_type)
        assert mocked_retry_async.call_args[1]["args"][2].get("Content-Type") == "application/octet-stream"


@pytest.fixture
def restore_buildhub_file():
    original_location = "tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/buildhub.json"
    copy_location = "tests/buildhub_copy.json"
    shutil.copy(original_location, copy_location)
    yield
    shutil.move(copy_location, original_location)


# move_beets {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("partials", (False, True))
async def test_move_beets(partials, mocker, restore_buildhub_file):
    mocker.patch("beetmoverscript.utils.JINJA_ENV", get_test_jinja_env())

    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task(taskjson="task_artifact_map.json")
    context.release_props = context.task["payload"]["releaseProperties"]
    context.release_props["stage_platform"] = context.release_props["platform"]
    context.resource = "nightly"
    context.action = "push-to-nightly"
    context.raw_balrog_manifest = dict()
    context.balrog_manifest = list()
    context.artifacts_to_beetmove = get_upstream_artifacts(context)
    artifact_map = context.task["payload"]["artifactMap"]

    expected_sources = [
        os.path.abspath("tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.mozinfo.json"),
        os.path.abspath("tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.txt"),
        os.path.abspath("tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target_expires.txt"),
        os.path.abspath("tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target_info.txt"),
        os.path.abspath("tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.test_packages.json"),
        os.path.abspath("tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/buildhub.json"),
        os.path.abspath("tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.apk"),
    ]
    expected_destinations = [
        [
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_info.txt",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_info.txt",
        ],
        [
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.mozinfo.json",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.mozinfo.json",
        ],
        [
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
        ],
        [
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_expires.txt",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_expires.txt",
        ],
        [
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.test_packages.json",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.test_packages.json",
        ],
        [
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.buildhub.json",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.buildhub.json",
        ],
        [
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.apk",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.apk",
        ],
    ]
    expected_expires = [
        "2034-02-03T04:05:06.123Z",
    ]

    expected_balrog_manifest = []
    for complete_info in [
        {
            "completeInfo": [
                {
                    "hash": "dummyhash",
                    "size": 123456,
                    "url": "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_info.txt",
                }
            ]
        },
        {
            "blob_suffix": "-mozinfo",
            "completeInfo": [
                {
                    "hash": "dummyhash",
                    "size": 123456,
                    "url": "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.mozinfo.json",
                }
            ],
        },
    ]:
        entry = {
            "tc_nightly": True,
            "appName": "Fake",
            "appVersion": "99.0a1",
            "branch": "mozilla-central",
            "buildid": "20990205110000",
            "extVersion": "99.0a1",
            "hashType": "sha512",
            "locale": "en-US",
            "platform": "android-api-15",
            "url_replacements": [["http://archive.mozilla.org/pub", "http://download.cdn.mozilla.net/pub"]],
        }
        entry.update(complete_info)
        if partials:
            entry["partialInfo"] = [
                {
                    "from_buildid": 19991231235959,
                    "hash": "dummyhash",
                    "size": 123456,
                    "url": "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
                }
            ]
        expected_balrog_manifest.append(entry)

    actual_sources = []
    actual_destinations = []
    actual_expires = []

    def sort_manifest(manifest):
        manifest.sort(key=lambda entry: entry.get("blob_suffix", ""))

    async def fake_move_beet(context, source, destinations, locale, update_balrog_manifest, balrog_format, artifact_pretty_name, from_buildid, expiry=None):
        actual_sources.append(source)
        actual_destinations.append(destinations)
        if expiry:
            actual_expires.append(expiry)
        if update_balrog_manifest:
            data = {"hash": "dummyhash", "size": 123456, "url": destinations[0]}
            context.raw_balrog_manifest.setdefault(locale, {})
            if from_buildid:
                if partials:
                    data["from_buildid"] = from_buildid
                    context.raw_balrog_manifest[locale].setdefault("partialInfo", []).append(data)
                else:
                    return
            else:
                context.raw_balrog_manifest[locale].setdefault("completeInfo", {})[balrog_format] = data

    with mock.patch("beetmoverscript.script.move_beet", fake_move_beet):
        await move_beets(context, context.artifacts_to_beetmove, artifact_map=artifact_map)

    assert sorted(expected_sources) == sorted(actual_sources)
    assert sorted(expected_destinations) == sorted(actual_destinations)
    assert sorted(expected_expires) == sorted(actual_expires)

    # Deal with different-sorted completeInfo
    sort_manifest(context.balrog_manifest)
    sort_manifest(expected_balrog_manifest)
    assert context.balrog_manifest == expected_balrog_manifest


# move_beets {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("task_filename", ("task.json", "task_missing_installer.json"))
async def test_move_beets_raises(mocker, task_filename):
    mocker.patch("beetmoverscript.utils.JINJA_ENV", get_test_jinja_env())

    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task(taskjson=task_filename)
    context.release_props = context.task["payload"]["releaseProperties"]
    context.release_props["stage_platform"] = context.release_props["platform"]
    context.resource = "nightly"
    context.action = "push-to-nightly"
    context.raw_balrog_manifest = dict()
    context.balrog_manifest = list()
    context.artifacts_to_beetmove = get_upstream_artifacts(context)

    with pytest.raises(ScriptWorkerTaskException):
        await move_beets(context, context.artifacts_to_beetmove, artifact_map={})


# move_beet {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update_manifest,action", [(True, "push-to-candidates"), (True, "push-to-nightly"), (False, "push-to-nightly"), (False, "push-to-candidates")]
)
async def test_move_beet(update_manifest, action):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.task["extra"] = dict()
    context.task["extra"]["partials"] = [
        {
            "artifact_name": "target-98.0b96.partial.mar",
            "platform": "linux",
            "locale": "de",
            "buildid": "19991231235959",
            "previousVersion": "98.0b96",
            "previousBuildNumber": "1",
        },
        {
            "artifact_name": "target-97.0b96.partial.mar",
            "platform": "linux",
            "locale": "de",
            "buildid": "22423423402984",
            "previousVersion": "97.0b96",
            "previousBuildNumber": "1",
        },
    ]
    context.action = action
    context.resource = "nightly"
    context.checksums = dict()
    context.balrog_manifest = list()
    context.raw_balrog_manifest = dict()
    context.release_props = context.task["payload"]["releaseProperties"]
    locale = "sample-locale"

    target_source = "tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.txt"
    pretty_name = "fake-99.0a1.en-US.target.txt"
    target_destinations = (
        "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
        "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
    )
    expected_upload_args = [
        (
            "pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
            "pub/mobile/nightly/latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
        ),
        "tests/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.txt",
    ]
    expected_balrog_manifest = {
        "hash": "73b91c3625d70e9ba1992f119bdfd3fba85041e6f804a985a18efe06ebb1d4147fb044ac06b28773130b4887dd8b5b3bc63958e1bd74003077d8bc2a3909416b",
        "size": 18,
        "url": "https://archive.test/pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target.txt",
    }
    actual_upload_args = []

    async def fake_retry_upload(context, destinations, path, expiry=None):
        actual_upload_args.extend([destinations, path])

    with mock.patch("beetmoverscript.script.retry_upload", fake_retry_upload):
        await move_beet(
            context,
            target_source,
            target_destinations,
            locale,
            update_balrog_manifest=update_manifest,
            balrog_format="",
            artifact_pretty_name=pretty_name,
            from_buildid=None,
        )
    assert expected_upload_args == actual_upload_args
    if update_manifest:
        for k in expected_balrog_manifest.keys():
            assert context.raw_balrog_manifest[locale]["completeInfo"][""][k] == expected_balrog_manifest[k]

    expected_balrog_manifest["from_buildid"] = "19991231235959"
    with mock.patch("beetmoverscript.script.retry_upload", fake_retry_upload):
        await move_beet(
            context,
            target_source,
            target_destinations,
            locale,
            update_balrog_manifest=update_manifest,
            balrog_format="",
            artifact_pretty_name=pretty_name,
            from_buildid="19991231235959",
        )
    if update_manifest:
        if is_promotion_action(context.action):
            expected_balrog_manifest["previousBuildNumber"] = "1"
            expected_balrog_manifest["previousVersion"] = "98.0b96"
        for k in expected_balrog_manifest.keys():
            assert context.raw_balrog_manifest[locale]["partialInfo"][0][k] == expected_balrog_manifest[k]


# move_partner_beets {{{1
@pytest.mark.asyncio
async def test_move_partner_beets(context, mocker):
    context.artifacts_to_beetmove = get_upstream_artifacts(context, preserve_full_paths=True)
    context.release_props = get_release_props(context.task)
    context.checksums = dict()
    mocker.patch("beetmoverscript.utils.JINJA_ENV", get_test_jinja_env())
    mapping_manifest = generate_beetmover_manifest(context)

    mocker.patch.object(beetmoverscript.script, "get_destination_for_partner_repack_path", new=lambda *args: "")
    mocker.patch.object(beetmoverscript.script, "upload_to_s3", new=noop_async)
    mocker.patch.object(beetmoverscript.script, "upload_to_gcs", new=noop_async)
    await move_partner_beets(context, mapping_manifest)


# get_destination_for_partner_repack_path {{{1
@pytest.mark.parametrize(
    "full_path,expected,bucket,raises,locale",
    (
        (
            "releng/partner/ghost/ghost-variant/en-US/target.tar.bz2",
            "pub/firefox/candidates/9999.0-candidates/build99/partner-repacks/ghost/ghost-variant/v1/linux-i686/en-US/firefox-9999.0.tar.bz2",
            "dep",
            True,
            "partner-repacks/ghost/ghost-variant/v1/linux-i686/en-US",
        ),
        (
            "releng/partner/ghost/ghost-variant/en-US/target.tar.bz2",
            "pub/firefox/candidates/9999.0-candidates/build99/partner-repacks/ghost/ghost-variant/v1/linux-i686/en-US/firefox-9999.0.tar.bz2",
            "dep",
            False,
            "partner-repacks/ghost/ghost-variant/v1/linux-i686/en-US",
        ),
        (
            "releng/partner/ghost/ghost-variant/en-US/target.tar.xz",
            "pub/firefox/candidates/9999.0-candidates/build99/partner-repacks/ghost/ghost-variant/v1/linux-i686/en-US/firefox-9999.0.tar.xz",
            "dep",
            False,
            "partner-repacks/ghost/ghost-variant/v1/linux-i686/en-US",
        ),
    ),
)
def test_get_destination_for_partner_repack_path(context, full_path, expected, bucket, raises, locale):
    context.resource = bucket
    context.action = "push-to-partner"
    context.task["payload"]["build_number"] = 99
    context.task["payload"]["version"] = "9999.0"
    context.task["payload"]["releaseProperties"] = {
        "appName": "Firefox",
        "buildid": "20180328233904",
        "appVersion": "9999.0",
        "hashType": "sha512",
        "platform": "linux",
        "branch": "maple",
    }
    # hack in locale
    for artifact_dict in context.task["payload"]["upstreamArtifacts"]:
        artifact_dict["locale"] = locale
    context.artifacts_to_beetmove = get_upstream_artifacts(context, preserve_full_paths=True)
    context.release_props = get_release_props(context.task)
    mapping_manifest = generate_beetmover_manifest(context)

    if raises:
        context.action = "push-to-dummy"
        with pytest.raises(ScriptWorkerRetryException):
            get_destination_for_partner_repack_path(context, mapping_manifest, full_path, locale)
    else:
        assert expected == get_destination_for_partner_repack_path(context, mapping_manifest, full_path, locale)


# sanity_check_partner_path {{{1
@pytest.mark.parametrize(
    "path,raises",
    (
        ("foo/bar", True),
        ("foo/9999-1/bar/mac/baz", True),
        ("../9999-1/bar/mac/baz", True),
        ("foo/9999-1/../mac/baz", True),
        ("foo/9999-1/bar/badplatform/baz", True),
        ("mac-EME-free/foo", False),
        ("badplatform-EME-free/foo", True),
        ("partner-repacks/foo/foo-bar/v1/win32/en-US", False),
        ("partner-repacks/foo/foo-bar/v1/badplatform/en-US", True),
        ("partner-repacks/foo/foo-bar/v1/win32/en-US/extra", True),
    ),
)
def test_sanity_check_partner_path(path, raises):
    repl_dict = {"version": "9999", "build_number": 1}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            sanity_check_partner_path(path, repl_dict, PARTNER_REPACK_REGEXES)
    else:
        sanity_check_partner_path(path, repl_dict, PARTNER_REPACK_REGEXES)


# async_main {{{1
@pytest.mark.parametrize(
    "action,raises,task_filename",
    (("push-to-nightly", False, "task_artifact_map.json"), ("push-to-unknown", True, "task.json")),
)
@pytest.mark.asyncio
async def test_async_main(context, mocker, action, raises, task_filename):
    context.action = action
    context.task = get_fake_valid_task(taskjson=task_filename)

    def fake_action(*args, **kwargs):
        return action

    mocker.patch("beetmoverscript.utils.JINJA_ENV", get_test_jinja_env())
    mocker.patch("beetmoverscript.script.move_beets", new=noop_async)
    mocker.patch.object(beetmoverscript.script, "get_task_action", new=fake_action)
    mocker.patch("beetmoverscript.gcloud.setup_gcs_credentials", new=noop_sync)
    mocker.patch("beetmoverscript.gcloud.set_gcp_client", new=noop_sync)
    mocker.patch("beetmoverscript.gcloud.cleanup_gcloud", new=noop_sync)
    if raises:
        with pytest.raises(SystemExit):
            await async_main(context)
    else:
        await async_main(context)

    for module in ("botocore", "boto3", "chardet"):
        assert logging.getLogger(module).level == logging.INFO


# main {{{1
def test_main(fake_session):
    context = Context()
    context.config = get_fake_valid_config()

    async def fake_async_main(context):
        pass

    async def fake_async_main_with_exception(context):
        raise ScriptWorkerTaskException("This is wrong, the answer is 42")

    with mock.patch("beetmoverscript.script.async_main", new=fake_async_main):
        main(config_path="tests/fake_config.json")

    with mock.patch("beetmoverscript.script.async_main", new=fake_async_main_with_exception):
        try:
            main(config_path="tests/fake_config.json")
        except SystemExit as exc:
            assert exc.code == 1
