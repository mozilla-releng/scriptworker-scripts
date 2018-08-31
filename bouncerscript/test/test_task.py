import pytest

from scriptworker.exceptions import (
    ScriptWorkerTaskException, TaskVerificationError
)

import bouncerscript.task as btask
from bouncerscript.task import (
    get_supported_actions, get_task_server, get_task_action,
    validate_task_schema, check_product_names_match_aliases,
    check_locations_match, check_path_matches_destination,
    check_aliases_match
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
    config = {
        'taskcluster_scope_prefix': 'project:releng:bouncer:',
        'bouncer_config': {'project:releng:bouncer:server:staging': ''},
    }
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
        'taskcluster_scope_prefix': 'project:releng:bouncer:',
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


# check_locations_match {{{1
@pytest.mark.parametrize("locations, product_config, raises", ((
    ['a', 'b'], {'aaaa': 'a', 'bbbb': 'b'},
    False,
), (
    ['a', 'b'], {'aaaa': 'b', 'bbbb': 'a'},
    False,
), (
    [], {},
    False,
), (
    [
        '/mobile/releases/62.0b10/android-x86/:lang/fennec-62.0b10.:lang.android-i386.apk',
        '/mobile/releases/62.0b10/android-api-16/:lang/fennec-62.0b10.:lang.android-arm.apk',
    ],
    {
        "android": "/mobile/releases/62.0b10/android-api-16/:lang/fennec-62.0b10.:lang.android-arm.apk",
        "android-x86": "/mobile/releases/62.0b10/android-x86/:lang/fennec-62.0b10.:lang.android-i386.apk"
    },
    False,
), (
    ['a'], {'a': 'b'},
    True,
), (
    [], {'a': 'b'},
    True,
)))
def test_check_locations_match(locations, product_config, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_locations_match(locations, product_config)
    else:
        check_locations_match(locations, product_config)


# check_path_matches_destination {{{1
@pytest.mark.parametrize("product_name, path, raises", (((
    "Firefox-61.0b15-SSL",
    "/firefox/releases/61.0b15/mac/:lang/Firefox%2061.0b15.dmg",
    False,
), (
    "Fennec-61.0b15",
    "/mobile/releases/61.0b15/android-x86/:lang/fennec-61.0b15.:lang.android-i386.apk",
    False,
), (
    "Fennec-61.0b15",
    "/mobile/releases/61.0b15/android-x86/:lang/fennec-61.0b15.:lang.android-i386.apk",
    False,
), (
    "Fennec-61.0b15",
    "/firefox/releases/61.0b15/update/mac/:lang/firefox-61.0b15-61.0b15.partial.mar",
    True,
), (
    "Firefox-61.0b15",
    "/firefox/releases/61.0b15/linux-x86_64/:lang/firefox-61.0b15.tar.bz2",
    False,
), (
    "Firefox-61.0b15",
    "/firefox/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe",
    False,
), (
    "Firefox-61.0b15",
    "/firefox/releases/61.0b15/mac/:lang/Firefox%2061.0b15.dmg",
    False,
), (
    "Firefox-61.0b15",
    "/devedition/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe",
    True,
), (
    "Firefox-61.0b15-Complete",
    "/firefox/releases/61.0b15/update/win64/:lang/firefox-61.0b15.complete.mar",
    False,
), (
    "Firefox-61.0b15-Complete",
    "/firefox/releases/61.0b15/update/linux-i686/:lang/firefox-61.0b15.complete.mar",
    False,
), (
    "Firefox-61.0b15-Complete",
    "/firefox/releases/61.0b15/update/mac/:lang/firefox-61.0b15.complete.marx",
    True,
), (
    "Firefox-61.0b15-Partial-61.0b15",
    "/firefox/releases/61.0b15/update/linux-x86_64/:lang/firefox-61.0b15-61.0b15.partial.mar",
    False,
), (
    "Firefox-61.0b15-Partial-61.0b15",
    "/firefox/releases/61.0b15/update/win32/:lang/fennec-61.0b15-61.0b15.partial.mar",
    True,
), (
    "Firefox-61.0b15-Partial-61.0b15",
    "/firefox/releases/61.0b15/update/win64/:lang/firefox-61.0b15-61.0b15.partial.mar",
    False,
), (
    "Firefox-61.0b15-SSL",
    "/firefox/releases/61.0b15/linux-i686/:lang/firefox-61.0b15.tar.bz2",
    False,
), (
    "Firefox-61.0b15-SSL",
    "/firefox/releases/61.0b15/win64/Firefox%20Setup%2061.0b15.exe",
    True,
), (
    "Firefox-61.0b15-SSL",
    "/firefox/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe",
    False,
), (
    "Firefox-61.0b15-stub",
    "/firefox/releases/61.0b15/win32/:lang/Firefox%20Installer.exe",
    False,
), (
    "Firefox-61.0b15-stub",
    "/firefox/releases/61.0b15/win32/:lang/Firefox%20Installer.exe",
    False,
), (
    "Firefox-61.0b15-stub",
    "/mobile/releases/61.0b15/win32/:lang/Firefox%20Installer.exe",
    True,
), (
    "Firefox-62.0build1-Partial-60.0.2build1",
    "/firefox/candidates/62.0-candidates/build1/update/linux-i686/:lang/firefox-60.0.2-62.0.partial.mar",
    False,
), (
    "Firefox-62.0build1-Partial-60.0.2build1",
    "/firefox/releases/62.0/update/linux-i686/:lang/firefox-60.0.2-62.0.partial.mar",
    True,
), (
    "Devedition-61.0b15",
    "/devedition/releases/61.0b15/linux-i686/:lang/firefox-61.0b15.tar.bz2",
    False,
), (
    "Devedition-61.0b15",
    "/firefox/releases/61.0b15/linux-x86_64/:lang/firefox-61.0b15.tar.bz2",
    True,
), (
    "Devedition-61.0b15-Complete",
    "/devedition/releases/61.0b15/update/mac/:lang/firefox-61.0b15.complete.mar",
    False,
), (
    "Devedition-61.0b15-Complete",
    "/devedition/releases/61.0b15/:lang/firefox-61.0b15.complete.mar",
    True,
), (
    "Devedition-61.0b15-Partial-61.0b15",
    "/devedition/releases/update/win32/:lang/firefox-61.0b15-61.0b15.partial.mar",
    False,
), (
    "Devedition-61.0b15-Partial-61.0b15",
    "/devedition/releases/update/lang/firefox-61.0b15-61.0b15.partial.mar",
    True,
), (
    "Devedition-61.0b15-SSL",
    "/devedition/releases/61.0b15/linux-i686/:lang/firefox-61.0b15.tar.bz2",
    False,
), (
    "Devedition-61.0b15-SSL",
    "/devedition/releases/61.0b15/win64/:lang/Devedition%20Setup%2061.0b15.exe",
    True,
), (
    "Devedition-61.0b15-SSL",
    "/devedition/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe",
    False,
), (
    "Devedition-61.0b15-stub",
    "/devedition/releases/61.0b15/win32/:lang/Firefox%20Installer.exe",
    False,
), (
    "Devedition-61.0b15-stub",
    "/devedition/releases/61.0b15/win32/:lang/Firefox%20Installer.exe",
    False,
), (
    "Devedition-61.0b15-stub",
    "/devedition/candidates/61.0b15/win32/:lang/Firefox%20Installer.exe",
    True,
), (
    "Thunderbird-62.0b7",
    "/thunderbird/releases/62.0b7/mac/:lang/Thunderbird%2062.0b7.dmg",
    False,
), (
    "Thunderbird-62.0b7",
    "/firefox/releases/62.0b7/win32/:lang/Thunderbird%20Setup%2062.0b7.exe",
    True,
), (
    "Thunderbird-62.0b7-Complete",
    "/thunderbird/releases/62.0b7/update/mac/:lang/thunderbird-62.0b7.complete.mar",
    False,
), (
    "Thunderbird-62.0b7-Complete",
    "/thunderbird/releases/62.0b7/update/linux-x86_64/:lang/thunderbird-62.0b7.complete.mar",
    False,
), (
    "Thunderbird-62.0b7-Complete",
    "/thunderbird/releases/62.0b7/update/win64/:lang/thunderbird-62.0b7.complete.mar",
    False,
), (
    "Thunderbird-62.0b7-Complete",
    "/thunderbird/releases/62.0b7/update/win64/:lang/thunderbird-62.0b7.complete.partial",
    True,
), (
    "Thunderbird-62.0b7-SSL",
    "/thunderbird/releases/62.0b7/win64/:lang/Thunderbird%20Setup%2062.0b7.exe",
    False,
), (
    "Thunderbird-62.0b7-SSL",
    "/thunderbird/releases/62.0b7/mac/:lang/Thunderbird%2062.0b7.dmg",
    False,
), (
    "Thunderbird-62.0b7-SSL",
    "/thunderbird/releases/62.0b7/linux-i686/:lang/thunderbird-62.0b7.tar.bz2",
    False,
), (
    "Thunderbird-62.0b7-SSL",
    "/thunderbird/candidates/62.0b7/linux-x86_64/:lang/thunderbird-62.0b7.tar.bz2",
    True,
))))
def test_check_path_matches_destination(product_name, path, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_path_matches_destination(product_name, path)
    else:
        check_path_matches_destination(product_name, path)


# check_aliases_match {{{1
@pytest.mark.parametrize("entries,provided,raises", (((
    {
        "fennec-beta-latest": "Fennec-62.0b5",
        "fennec-latest": "Fennec-61.0",
    },
    {
        ("https://download.mozilla.org/?product="
         "fennec-beta-latest&print=yes"): "404 page not found\n",
        ("https://download.mozilla.org/?product="
         "fennec-latest&print=yes"): "404 page not found\n",
        ("https://download.mozilla.org/?product="
         "thunderbird-next-latest-ssl&print=yes"): "404 page not found\n",
        ("https://download.mozilla.org/?product="
         "thunderbird-next-latest&print=yes"): "404 page not found\n",
        ("https://download.mozilla.org/?product="
         "thunderbird-latest-ssl&print=yes"): "404 page not found\n",
    },
    False,
), (
    {
        "firefox-latest": "Firefox-61.0.1",
        "firefox-latest-ssl": "Firefox-61.0.1-SSL",
        "firefox-stub": "Firefox-61.0.1-stub"
    },
    {
        ("https://download.mozilla.org/?product="
         "firefox-latest&print=yes"): ("https://download-installer.cdn."
                                       "mozilla.net/pub/firefox/releases/"
                                       "61.0.1/win32/en-US/Firefox%20Setup"
                                       "%2061.0.1.exe"),
        ("https://download.mozilla.org/?product="
         "firefox-latest-ssl&print=yes"): ("https://download-installer.cdn."
                                           "mozilla.net/pub/firefox/releases/"
                                           "61.0.1/win32/en-US/Firefox%20Setup"
                                           "%2061.0.1.exe"),
        ("https://download.mozilla.org/?product="
         "firefox-stub&print=yes"): ("https://download-installer.cdn.mozilla."
                                     "net/pub/firefox/releases/61.0.1/win32/"
                                     "en-US/Firefox%20Installer.exe"),
        ("https://download.mozilla.org/?product="
         "Firefox-61.0.1&print=yes"): ("https://download-installer.cdn.mozilla."
                                       "net/pub/firefox/releases/61.0.1/win32/"
                                       "en-US/Firefox%20Setup%2061.0.1.exe"),
        ("https://download.mozilla.org/?product="
         "Firefox-61.0.1-SSL&print=yes"): ("https://download-installer.cdn."
                                           "mozilla.net/pub/firefox/releases/"
                                           "61.0.1/win32/en-US/Firefox%20Setup"
                                           "%2061.0.1.exe"),
        ("https://download.mozilla.org/?product="
         "Firefox-61.0.1-stub&print=yes"): ("https://download-installer.cdn."
                                            "mozilla.net/pub/firefox/releases/"
                                            "61.0.1/win32/en-US/Firefox%20Installer.exe"),
    },
    False,
), (
    {
        "thunderbird-next-latest": "Thunderbird-62.0",
        "thunderbird-next-latest-ssl": "Thunderbird-62.0",
        "thunderbird-latest-ssl": "Thunderbird-62.0",
    },
    {
        ("https://download.mozilla.org/?product="
         "thunderbird-next-latest-ssl&print=yes"): "404 page not found\n",
        ("https://download.mozilla.org/?product="
         "thunderbird-next-latest&print=yes"): "404 page not found\n",
        ("https://download.mozilla.org/?product="
         "thunderbird-latest-ssl&print=yes"): "404 page not found\n",
    },
    False,
), (
    {
        "firefox-latest": "Firefox-61.0.1",
    },
    {
        ("https://download.mozilla.org/?product="
         "firefox-latest&print=yes"): ("https://download-installer.cdn."
                                       "mozilla.net/pub/firefox/releases/"
                                       "61.0/win32/en-US/Firefox%20Setup"
                                       "%2061.0.1.exe"),
        ("https://download.mozilla.org/?product="
         "Firefox-61.0.1&print=yes"): ("https://download-installer.cdn.mozilla."
                                       "net/pub/firefox/releases/61.0.1/win32/"
                                       "en-US/Firefox%20Setup%2061.0.1.exe"),
    },
    True,
))))
@pytest.mark.asyncio
async def test_check_aliases_match(aliases_context, mocker, entries, provided, raises):
    async def fake_retry_request(context, url, good=(200,)):
        return provided[url]

    aliases_context.task["payload"]["aliases_entries"] = entries
    mocker.patch.object(btask, 'retry_request', new=fake_retry_request)

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            await check_aliases_match(aliases_context)
    else:
        await check_aliases_match(aliases_context)
