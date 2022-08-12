import os

import pytest
from google.api_core.exceptions import Forbidden
from google.auth.exceptions import DefaultCredentialsError
from scriptworker.exceptions import ScriptWorkerTaskException

import beetmoverscript.gcloud

from . import noop_sync


class FakeClient:
    class FakeBucket:
        def __init__(self, name):
            self.name = name

        def exists(self):
            return self.name == "existingbucket"

    def bucket(self, bucket_name):
        return self.FakeBucket(bucket_name)


@pytest.fixture(scope="function")
def mock_gcs(monkeypatch):
    monkeypatch.setattr(beetmoverscript.gcloud, "Client", FakeClient)


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


def test_set_gcs_client(context, mock_gcs, monkeypatch):
    # Bucket won't exist by default
    beetmoverscript.gcloud.set_gcs_client(context)

    monkeypatch.setattr(beetmoverscript.gcloud, "get_bucket_name", lambda *x: "existingbucket")
    beetmoverscript.gcloud.set_gcs_client(context)


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
    TARGET_PATH = "/target_path"
    PATH = "/hello.zip"

    class FakeBucket:
        def __init__(self, *args, **kwargs):
            pass

        class FakeBlob:
            content_type = ""
            cache_control = ""

            def upload_from_filename(self, path, content_type):
                assert path == PATH
                assert content_type == "application/zip"

        def blob(self, path):
            assert path == TARGET_PATH
            return self.FakeBlob()

    context.gcs_client = "FakeClient"
    monkeypatch.setattr(beetmoverscript.gcloud, "Bucket", FakeBucket)
    await beetmoverscript.gcloud.upload_to_gcs(context, TARGET_PATH, PATH)
