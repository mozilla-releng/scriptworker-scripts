import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.script import get_default_config
from signingscript.task import task_signing_formats, task_cert_type, validate_task_schema

from signingscript.test.helpers import task_generator


def test_task_signing_formats():
    task = {"scopes": ["project:releng:signing:cert:dep-signing",
                       "project:releng:signing:format:mar",
                       "project:releng:signing:format:gpg"]}
    assert ["mar", "gpg"] == task_signing_formats(task)


def test_task_cert_type():
    task = {"scopes": ["project:releng:signing:cert:dep-signing",
                       "project:releng:signing:type:mar",
                       "project:releng:signing:type:gpg"]}
    assert "project:releng:signing:cert:dep-signing" == task_cert_type(task)


def test_task_cert_type_error():
    task = {"scopes": ["project:releng:signing:cert:dep-signing",
                       "project:releng:signing:cert:notdep",
                       "project:releng:signing:type:gpg"]}
    with pytest.raises(ScriptWorkerTaskException):
        task_cert_type(task)


@pytest.fixture
def context():
    context = Context()
    context.config = get_default_config()
    return context


def test_missing_mandatory_urls_are_reported(context):
    context.task = task_generator.generate_object(urls=[])  # no URLs provided

    with pytest.raises(ScriptWorkerTaskException):
        validate_task_schema(context)


def test_no_error_is_reported_when_no_missing_url(context):
    context.task = task_generator.generate_object()
    validate_task_schema(context)
