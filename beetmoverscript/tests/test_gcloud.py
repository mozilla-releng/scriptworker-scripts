import os

import pytest
from google.api_core.exceptions import Forbidden
from google.auth.exceptions import DefaultCredentialsError
from scriptworker.exceptions import ScriptWorkerTaskException

import beetmoverscript.gcloud

from . import get_fake_valid_task, noop_sync


class FakeClient:
    class FakeBlob:
        PATH = "/foo.zip"
        _exists = False

        content_type = ""
        cache_control = ""
        name = "fakename"
        md5_hash = "fakemd5hash"

        def copy_blob(*args):
            pass

        def upload_from_filename(self, path, content_type):
            assert path == self.PATH
            assert content_type == "application/zip"

        def exists(self):
            return self._exists

    class FakeBucket:
        FAKE_BUCKET_NAME = "existingbucket"

        def __init__(self, client, name, *args):
            self.client = client
            self.name = name

        def exists(self):
            return self.name == self.FAKE_BUCKET_NAME

        def blob(*args):
            return FakeClient.FakeBlob()

        def copy_blob(*args):
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
    # Withoutch gcs_client set
    beetmoverscript.gcloud.cleanup_gcloud(context)

    # With gcs_client set
    context.gcs_client = True
    monkeypatch.setattr(beetmoverscript.gcloud.os, "remove", noop_sync)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "something")
    beetmoverscript.gcloud.cleanup_gcloud(context)


def test_setup_gcloud(monkeypatch, context):
    monkeypatch.setattr(beetmoverscript.gcloud, "setup_gcs_credentials", noop_sync)
    monkeypatch.setattr(beetmoverscript.gcloud, "set_gcs_client", noop_sync)

    beetmoverscript.gcloud.setup_gcloud(context)

    # Should just skip without a cloud set
    context.bucket = "NotACloud"
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
    beetmoverscript.gcloud.set_gcs_client(context)
    assert hasattr(context, "gcs_client") == client_set


@pytest.mark.parametrize("exception", (Forbidden, DefaultCredentialsError, Exception))
def test_set_gcs_client_fails(monkeypatch, context, exception):
    class ErrorClient:
        def __init__(self):
            raise exception("ErrorClient")

    monkeypatch.setattr(beetmoverscript.gcloud, "Client", ErrorClient)
    # with fail_task_on_error
    with pytest.raises(exception):
        beetmoverscript.gcloud.set_gcs_client(context)

    # without fail_task_on_error
    context.config["clouds"]["gcloud"]["nightly"]["fail_task_on_error"] = False
    beetmoverscript.gcloud.set_gcs_client(context)


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


@pytest.mark.asyncio
async def test_upload_to_gcs_fail(context):
    with pytest.raises(ScriptWorkerTaskException):
        await beetmoverscript.gcloud.upload_to_gcs(context, "/target_path", "/noextension")


@pytest.mark.asyncio
async def test_upload_to_gcs(context, monkeypatch):
    context.gcs_client = "FakeClient"
    monkeypatch.setattr(beetmoverscript.gcloud, "Bucket", FakeClient.FakeBucket)
    await beetmoverscript.gcloud.upload_to_gcs(context, "path/target", FakeClient.FakeBlob.PATH)
    # With existing file
    monkeypatch.setattr(beetmoverscript.gcloud, "Bucket", FakeClient.FakeBucketExisting)
    await beetmoverscript.gcloud.upload_to_gcs(context, "path/target", FakeClient.FakeBlob.PATH)


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


def test_list_bucket_objects_gcs():
    beetmoverscript.gcloud.list_bucket_objects_gcs(FakeClient(), "foobucket", "prefix")
