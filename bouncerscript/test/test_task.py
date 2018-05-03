import pytest

from scriptworker.exceptions import (
    ScriptWorkerTaskException, TaskVerificationError
)

from bouncerscript.task import (
    get_supported_actions, get_task_server, get_task_action,
    validate_task_schema, check_product_names_match_aliases
)
from bouncerscript.test import submission_context as context
from bouncerscript.test import aliases_context


assert context  # silence pyflakes
assert aliases_context  # silence pyflakes


# get_task_server {{{1
@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:bouncer:server:staging",
     "project:releng:bouncer:server:production"],
    None, True,
), (
    ["project:releng:bouncer:server:!!"],
    None, True
), (
    ["project:releng:bouncer:server:staging",
     "project:releng:bouncer:action:foo"],
    "project:releng:bouncer:server:staging", False
)))
def test_get_task_server(scopes, expected, raises):
    task = {'scopes': scopes}
    config = {'bouncer_config': {'project:releng:bouncer:server:staging': ''}}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_server(task, config)
    else:
        assert expected == get_task_server(task, config)


# get_task_action {{{1
@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:bouncer:action:submission",
     "project:releng:bouncer:action:aliases"],
    None, True
), (
    ["project:releng:bouncer:action:invalid"],
    None, True
), (
    ["project:releng:bouncer:action:submission"],
    "submission", False
), (
    ["project:releng:bouncer:action:aliases"],
    "aliases", False
)))
def test_get_task_action(scopes, expected, raises):
    task = {'scopes': scopes}
    config = {
        'schema_files': {
            'submission': '/some/path.json',
            'aliases': '/some/other_path.json',
        },
    }
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_action(task, config)
    else:
        assert expected == get_task_action(task, config)


# get_supported_actions {{{1
def test_get_supported_actions():
    config = {
        'schema_files': {
            'submission': '/some/path.json',
            'aliases': '/some/other_path.json',
        },
    }
    assert sorted(get_supported_actions(config)) == sorted(('submission', 'aliases'))


# validate_task_schema {{{1
def test_validate_task_schema(context, schema="submission"):
    validate_task_schema(context)


# check_product_names_match_aliases {{{1
@pytest.mark.parametrize("entries,raises", (({
    "firefox-devedition-latest": "Devedition-70.0b2",
}, False
), ({
    "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL",
}, False
), ({
    "firefox-devedition-stub": "Devedition-70.0b2-stub"
}, False
), ({
    "firefox-devedition-latest": "Devedition-70.0",
}, True
), ({
    "firefox-devedition-latest-ssl": "Devedition-70.0.1-SSL",
}, True
), ({
    "firefox-devedition-stub": "Devedition-70.0-stub"
}, True
), ({
    "firefox-devedition-latest": "Devedition-70.0b2",
    "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL",
    "firefox-devedition-stub": "Devedition-70.0b2-stub"
}, False
), ({
    "firefox-devedition-latest": "Devedition-70.0b2",
    "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL",
    "firefox-devedition-stub": "Devedition-70.0-stub"
}, True
), ({
    "firefox-devedition-latest": "Devedition-70.02",
    "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL",
    "firefox-devedition-stub": "Devedition-70.0.1-stub"
}, True
), ({
    "firefox-beta-latest": "Firefox-70.0b2",
}, False
), ({
    "firefox-beta-latest-ssl": "Firefox-70.0b2-SSL",
}, False
), ({
    "firefox-beta-stub": "Firefox-70.0b2-stub"
}, False
), ({
    "firefox-beta-latest": "Firefox-70.0",
}, True
), ({
    "firefox-beta-latest-ssl": "Firefox-70.0.1-SSL",
}, True
), ({
    "firefox-beta-stub": "Firefox-70.0-stub"
}, True
), ({
    "firefox-beta-latest": "Firefox-70.0b2",
    "firefox-beta-latest-ssl": "Firefox-70.0b2-SSL",
    "firefox-beta-stub": "Firefox-70.0b2-stub"
}, False
), ({
    "firefox-beta-latest": "Firefox-70.0b2",
    "firefox-beta-latest-ssl": "Firefox-70.0b2-SSL",
    "firefox-beta-stub": "Firefox-70.0-stub"
}, True
), ({
    "firefox-beta-latest": "Firefox-70.02",
    "firefox-beta-latest-ssl": "Firefox-70.0b2-SSL",
    "firefox-beta-stub": "Firefox-70.0.1-stub"
}, True
), ({
    "firefox-latest": "Firefox-70.0",
}, False
), ({
    "firefox-latest-ssl": "Firefox-70.0.1-SSL",
}, False
), ({
    "firefox-stub": "Firefox-70.0.2-stub"
}, False
), ({
    "firefox-latest": "Firefox-70.0b1",
}, True
), ({
    "firefox-latest-ssl": "Firefox-70.0b1-SSL",
}, True
), ({
    "firefox-stub": "Firefox-70-stub"
}, True
), ({
    "firefox-latest": "Firefox-70.0",
    "firefox-latest-ssl": "Firefox-70.0-SSL",
    "firefox-stub": "Firefox-70.0-stub"
}, False
), ({
    "firefox-latest": "Firefox-70.0",
    "firefox-latest-ssl": "Firefox-70.0-SSL",
    "firefox-stub": "Firefox-70-stub"
}, True
), ({
    "firefox-latest": "Firefox-70.02",
    "firefox-latest-ssl": "Firefox-70.0b2-SSL",
    "firefox-stub": "Firefox-70-stub"
}, True
), ({
    "firefox-latest-ssl": "Firefox-59.0b14-SSL",
    "firefox-latest": "Firefox-59.0b14",
    "firefox-stub": "Firefox-59.0b14-stub"
}, True
), ({
    "firefox-esr-latest": "Firefox-70.1.0esr",
}, False
), ({
    "firefox-esr-latest-ssl": "Firefox-70.1.2esr-SSL",
}, False
), ({
    "firefox-esr-latest": "Firefox-70.2.1",
}, True
), ({
    "firefox-esr-latest-ssl": "Firefox-70.0b1-SSL",
}, True
), ({
    "firefox-esr-latest": "Firefox-70.1.0esr",
    "firefox-esr-latest-ssl": "Firefox-70.1.2esr-SSL",
}, False
), ({
    "firefox-esr-next-latest": "Firefox-70.1.0esr",
    "firefox-esr-next-latest-ssl": "Firefox-70.1.2esr-SSL",
}, False
), ({
    "firefox-esr-latest": "Firefox-70.1.0esr",
    "firefox-esr-latest-ssl": "Firefox-70.1.2-SSL",
}, True
), ({
    "firefox-esr-latest": "Firefox-70.1.0esr",
    "firefox-esr-latest-ssl": "Firefox-70.0b1-SSL",
}, True
), ({
    "firefox-sha1": "Firefox-52.7.2esr-sha1",
}, False
), ({
    "firefox-sha1-ssl": "Firefox-52.7.2esr-sha1",
}, False
), ({
    "firefox-sha1": "Firefox-70.1.0esr",
}, True
), ({
    "firefox-sha1-ssl": "Firefox-70.1.2esr",
}, True
), ({
    "firefox-sha1": "Firefox-52.7.2esr-sha1",
    "firefox-sha1-ssl": "Firefox-70.1.2esr-sha1",
}, False
), ({
    "firefox-sha1": "Firefox-70.1.0esr",
    "firefox-sha1-ssl": "Firefox-70.1.2-sha1",
}, True
), ({
    "firefox-sha1": "Firefox-70.1.0esr",
    "firefox-sha1-ssl": "Firefox-70.1.2esr-sha1",
}, True
), ({
    "fennec-beta-latest": "Fennec-70.0b2",
}, False
), ({
    "fennec-latest": "Fennec-70.0",
}, False
), ({
    "fennec-beta-latest": "Fennec-70.0",
}, True
), ({
    "fennec-latest": "Fennec-70.0.1-SSL",
}, True
), ({
    "fennec-beta-latest": "Fennec-70.0.1",
}, True
), ({
    "fennec-latest": "Fennec-70.0b1",
}, True
), ({
    "fennec-latest": "Fennec-70.0.1",
}, False
), ({
    "corrupt-alias": "corrupt-entry",
}, True
)))
def test_check_product_names_match_aliases(aliases_context, entries, raises):
    context = aliases_context
    context.task["payload"]["aliases_entries"] = entries
    if raises:
        with pytest.raises(TaskVerificationError):
            check_product_names_match_aliases(context)
    else:
        check_product_names_match_aliases(context)
