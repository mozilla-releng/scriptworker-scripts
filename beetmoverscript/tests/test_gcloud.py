import os
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import Forbidden
from google.api_core.retry import Retry
from google.auth.exceptions import DefaultCredentialsError
from google.cloud.storage.retry import DEFAULT_RETRY_IF_GENERATION_SPECIFIED, ConditionalRetryPolicy
from scriptworker.exceptions import ScriptWorkerTaskException

import beetmoverscript.gcloud
from beetmoverscript.utils import get_candidates_prefix, get_releases_prefix

from . import get_fake_valid_task, noop_sync


class FakeClient:
    class FakeBlob:
        def copy_blob(*args, **kwargs):
            pass

        def upload_from_filename(self, path, content_type, retry=DEFAULT_RETRY_IF_GENERATION_SPECIFIED, if_generation_match=None):
            assert path == self.PATH
            assert content_type == "application/zip"
            assert isinstance(retry, (Retry, ConditionalRetryPolicy))
            assert isinstance(if_generation_match, (int, type(None)))
            return self

        def exists(self):
            return self._exists

        def rewrite(self, source, *args, **kwargs):
            assert source

        def __init__(self) -> None:
            self.PATH = "/foo.zip"
            self._exists = False
            self.content_type = ""
            self.cache_control = ""
            self.name = "fakename"
            self.md5_hash = "fakemd5hash"
            self._properties = {}
            self.custom_time = None

    class FakeBucket:
        FAKE_BUCKET_NAME = "existingbucket"

        def __init__(self, client, name, *args):
            self.client = client
            self.name = name

        def exists(self):
            return self.name == self.FAKE_BUCKET_NAME

        def blob(*args):
            return FakeClient.FakeBlob()

        def get_blob(*args):
            return FakeClient.FakeBlob()

        def copy_blob(*args, **kwargs):
            pass

    class FakeBucketExisting(FakeBucket):
        def blob(*args):
            blob = FakeClient.FakeBlob()
            blob._exists = True
            return blob

    def bucket(self, bucket_name):
        return self.FakeBucket(self, bucket_name)

    def list_blobs(self, bucket, prefix):
        blob = self.FakeBlob()
        blob.name = f"{prefix}/{blob.name}"
        return [blob, blob, blob]


def test_cleanup_gcloud(monkeypatch, context):
    beetmoverscript.gcloud.cleanup_gcloud(context)
    monkeypatch.setattr(beetmoverscript.gcloud.os, "remove", noop_sync)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "something")
    beetmoverscript.gcloud.cleanup_gcloud(context)


def test_setup_gcloud(monkeypatch, context):
    monkeypatch.setattr(beetmoverscript.gcloud, "setup_gcs_credentials", noop_sync)
    monkeypatch.setattr(beetmoverscript.gcloud, "set_gcp_client", noop_sync)

    beetmoverscript.gcloud.setup_gcloud(context)

    # Should just skip without a cloud set
    context.resource = "NotACloud"
    beetmoverscript.gcloud.setup_gcloud(context)


@pytest.mark.parametrize(
    "bucket_name,client_set",
    [
        (FakeClient.FakeBucket.FAKE_BUCKET_NAME, True),
        ("nopebucket", False),
    ],
)
def test_set_gcs_client(context, monkeypatch, bucket_name, client_set):
    monkeypatch.setattr(beetmoverscript.gcloud, "Client", FakeClient)
    monkeypatch.setattr(beetmoverscript.gcloud, "get_bucket_name", lambda *x: bucket_name)
    beetmoverscript.gcloud.set_gcp_client(context)
    assert bool(context.gcs_client) == client_set


@pytest.mark.parametrize("exception", (Forbidden, DefaultCredentialsError, Exception))
def test_set_gcs_client_fails(monkeypatch, context, exception):
    class ErrorClient:
        def __init__(self):
            raise exception("ErrorClient")

    monkeypatch.setattr(beetmoverscript.gcloud, "Client", ErrorClient)
    # with fail_task_on_error
    with pytest.raises(exception):
        beetmoverscript.gcloud.set_gcp_client(context)

    # without fail_task_on_error
    context.config["clouds"]["gcloud"]["nightly"]["fail_task_on_error"] = False
    beetmoverscript.gcloud.set_gcp_client(context)


def test_setup_gcs_credentials(monkeypatch):
    BASE64CREDENTIALS = "eyJoZWxsbyI6ICJ3b3JsZCJ9\n"  # {"hello": "world"}

    class FakeTempFile:
        name = "fakename"

        def NamedTemporaryFile(*args, **kwargs):
            return FakeTempFile()

        def write(self, content):
            assert content == b'{"hello": "world"}'

        def close(self):
            pass

    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(beetmoverscript.gcloud, "tempfile", FakeTempFile)
    beetmoverscript.gcloud.setup_gcs_credentials(BASE64CREDENTIALS)
    assert str(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) == FakeTempFile.name
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)


@pytest.mark.parametrize(
    "path,expiry,exists,raise_class",
    (
        # Raise when can't find a mimetype
        ("foo/nomimetype", None, False, ScriptWorkerTaskException),
        # No expiration given
        ("foo/target.zip", None, False, None),
        # With expiration
        ("foo/target.zip", datetime.now().isoformat(), False, None),
        # With existing file
        ("foo/target.zip", None, True, None),
    ),
    ids=["no mimetype", "no expiry", "with expiry", "with existing file"],
)
@pytest.mark.asyncio
async def test_upload_to_gcs(context, monkeypatch, path, expiry, exists, raise_class):
    context.gcs_client = FakeClient()
    blob = FakeClient.FakeBlob()
    blob._exists = exists
    blob.upload_from_filename = MagicMock()
    bucket = FakeClient.FakeBucket(FakeClient, "foobucket")
    bucket.blob = MagicMock()
    bucket.blob.side_effect = [blob]
    log_warn = MagicMock()

    monkeypatch.setattr(beetmoverscript.gcloud, "Bucket", lambda client, name: bucket)
    monkeypatch.setattr(beetmoverscript.gcloud.log, "warning", log_warn)

    if raise_class:
        with pytest.raises(raise_class):
            await beetmoverscript.gcloud.upload_to_gcs(
                context=context,
                target_path="path/target",
                path=path,
                expiry=expiry,
            )
    else:
        await beetmoverscript.gcloud.upload_to_gcs(
            context=context,
            target_path="path/target",
            path=path,
            expiry=expiry,
        )

        if expiry:
            assert isinstance(blob.custom_time, datetime)
        else:
            assert blob.custom_time is None
        if exists:
            log_warn.assert_called()
        else:
            log_warn.assert_not_called()


@pytest.mark.parametrize(
    "candidate_blobs,release_blobs,partner_match,raises",
    [
        ({"foo/path": "md5hash"}, {"foo/path": "md5hash"}, None, False),
        ({"foo/path": "md5hash"}, {"foo/path": "oopsie"}, None, True),
        ({"foo/path": "md5hash"}, {}, None, False),
        ({"foo/tests/foo": "md5hash"}, {}, None, False),
        ({"foo/partner-repacks/bar": "md5hash"}, {}, None, False),
        ({"foo/partner-repacks/bar": "md5hash"}, {}, True, False),
        ({}, {}, None, True),
    ],
)
@pytest.mark.asyncio
async def test_push_to_releases_gcs_no_moves(context, monkeypatch, candidate_blobs, release_blobs, partner_match, raises):
    def fake_list_bucket_objects_gcs_same(client, bucket, prefix):
        if "candidates" in prefix:
            return {f"{prefix}{key}": value for (key, value) in candidate_blobs.items()}
        if "releases" in prefix:
            return {f"{prefix}{key}": value for (key, value) in release_blobs.items()}

    context.gcs_client = FakeClient()
    context.task = get_fake_valid_task("task_push_to_releases.json")
    monkeypatch.setattr(beetmoverscript.gcloud, "list_bucket_objects_gcs", fake_list_bucket_objects_gcs_same)
    monkeypatch.setattr(beetmoverscript.gcloud, "get_partner_match", lambda *x: partner_match)
    monkeypatch.setattr(beetmoverscript.gcloud, "get_partner_candidates_prefix", lambda *x: "fake_prefix")
    monkeypatch.setattr(beetmoverscript.gcloud, "Bucket", FakeClient.FakeBucket)
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            await beetmoverscript.gcloud.push_to_releases_gcs(context)
    else:
        await beetmoverscript.gcloud.push_to_releases_gcs(context)


@pytest.mark.parametrize(
    "candidate_blobs,exclude,results",
    [
        ({"foo/bar.zip": "md5hash", "foo/baz.exe": "abcd", "foo/qux.js": "shasum"}, [], ["foo/baz.exe", "foo/qux.js"]),
        ({"foo/bar.zip": "md5hash", "foo/baz.exe": "abcd", "foo/qux.js": "shasum"}, [r"^.*\.exe$"], ["foo/qux.js"]),
        ({"foo/bar.zip": "md5hash", "foo/baz.exe": "abcd", "foo/qux.js": "shasum"}, [r"^.*\.exe$", r"^.*\.js"], []),
    ],
)
@pytest.mark.asyncio
async def test_push_to_releases_gcs_exclude(context, monkeypatch, candidate_blobs, exclude, results):
    context.gcs_client = FakeClient()
    context.task = get_fake_valid_task("task_push_to_releases.json")

    payload = context.task["payload"]
    payload["exclude"] = exclude
    test_candidate_prefix = get_candidates_prefix(payload["product"], payload["version"], payload["build_number"])
    test_release_prefix = get_releases_prefix(payload["product"], payload["version"])

    def fake_list_bucket_objects_gcs_same(client, bucket, prefix):
        if "candidates" in prefix:
            return {f"{prefix}{key}": value for (key, value) in candidate_blobs.items()}
        if "releases" in prefix:
            return {}

    expect_blobs = {f"{test_candidate_prefix}{key}": f"{test_release_prefix}{key}" for key in results}

    def fake_move_artifacts(client, bucket_name, blobs_to_copy, candidates_blobs, releases_blobs):
        assert blobs_to_copy == expect_blobs

    monkeypatch.setattr(beetmoverscript.gcloud, "list_bucket_objects_gcs", fake_list_bucket_objects_gcs_same)
    monkeypatch.setattr(beetmoverscript.gcloud, "move_artifacts", fake_move_artifacts)

    await beetmoverscript.gcloud.push_to_releases_gcs(context)


def test_list_bucket_objects_gcs():
    beetmoverscript.gcloud.list_bucket_objects_gcs(FakeClient(), "foobucket", "prefix")


def test_move_artifacts_removing_custom_time(monkeypatch):
    source_blob = FakeClient.FakeBlob()
    source_blob.content_type = "application/x-xz"
    source_blob.cache_control = "public, max-age=100"
    dest_blob = FakeClient.FakeBlob()
    dest_blob.rewrite = MagicMock()
    bucket = FakeClient.FakeBucket(FakeClient, "foo")
    bucket.blob = MagicMock()
    bucket.blob.side_effect = [dest_blob]
    bucket.get_blob = MagicMock()
    bucket.get_blob.side_effect = [source_blob]

    monkeypatch.setattr(beetmoverscript.gcloud, "Bucket", lambda x, y: bucket)
    beetmoverscript.gcloud.move_artifacts(
        client=FakeClient,
        bucket_name=bucket.name,
        blobs_to_copy={"source/path": "destination/path"},
        candidates_blobs={},
        releases_blobs={},
    )
    # Setting name and bucket makes blob.rewrite remove any metadata from the source object
    assert dest_blob._properties.get("name") == "destination/path"
    assert dest_blob._properties.get("bucket") == bucket.name
    assert dest_blob.content_type == "application/x-xz"
    assert dest_blob.cache_control == "public, max-age=100"
    dest_blob.rewrite.assert_called_with(source=source_blob, retry=beetmoverscript.gcloud.DEFAULT_RETRY)


def test_move_artifacts_existing(monkeypatch):
    monkeypatch.setattr(beetmoverscript.gcloud, "Bucket", FakeClient.FakeBucket)
    # Throws exception if etags are different
    with pytest.raises(ScriptWorkerTaskException):
        beetmoverscript.gcloud.move_artifacts(
            client=FakeClient,
            bucket_name="foo",
            blobs_to_copy={"source/path": "destination/path"},
            candidates_blobs={"source/path": "different_etag2"},
            releases_blobs={"destination/path": "etag1"},
        )

    # Warns if same etags/content and no exception
    log_warn = MagicMock()
    monkeypatch.setattr(beetmoverscript.gcloud.log, "warning", log_warn)
    beetmoverscript.gcloud.move_artifacts(
        client=FakeClient,
        bucket_name="foo",
        blobs_to_copy={"source/path": "destination/path"},
        candidates_blobs={"source/path": "same_etag"},
        releases_blobs={"destination/path": "same_etag"},
    )
    log_warn.assert_called()
