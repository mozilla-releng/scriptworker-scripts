import pytest
from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.task import task_signing_formats, task_cert_type


def test_task_signing_formats():
    task = {"scopes": ["project:releng:signing:cert:dep",
                       "project:releng:signing:format:mar",
                       "project:releng:signing:format:gpg"]}
    assert ["mar", "gpg"] == task_signing_formats(task)


def test_task_cert_type():
    task = {"scopes": ["project:releng:signing:cert:dep",
                       "project:releng:signing:type:mar",
                       "project:releng:signing:type:gpg"]}
    assert "project:releng:signing:cert:dep" == task_cert_type(task)


def test_task_cert_type_error():
    task = {"scopes": ["project:releng:signing:cert:dep",
                       "project:releng:signing:cert:notdep",
                       "project:releng:signing:type:gpg"]}
    with pytest.raises(ScriptWorkerTaskException):
        task_cert_type(task)
