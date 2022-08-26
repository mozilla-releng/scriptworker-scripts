import pytest
from mozilla_version.errors import PatternNotMatchedError
from scriptworker.exceptions import ScriptWorkerTaskException, TaskVerificationError

import bouncerscript.task as btask
from bouncerscript.task import (
    check_aliases_match,
    check_location_path_matches_destination,
    check_locations_match,
    check_path_matches_destination,
    check_product_names_match_aliases,
    check_product_names_match_nightly_locations,
    check_version_matches_nightly_regex,
    check_versions_are_successive,
    get_supported_actions,
    get_task_action,
    get_task_server,
    validate_task_schema,
)


# get_task_server {{{1
@pytest.mark.parametrize(
    "scopes,expected,raises",
    (
        (["project:releng:bouncer:server:staging", "project:releng:bouncer:server:production"], None, True),
        (["project:releng:bouncer:server:!!"], None, True),
        (["project:releng:bouncer:server:staging", "project:releng:bouncer:action:foo"], "project:releng:bouncer:server:staging", False),
    ),
)
def test_get_task_server(scopes, expected, raises):
    task = {"scopes": scopes}
    config = {"taskcluster_scope_prefix": "project:releng:bouncer:", "bouncer_config": {"project:releng:bouncer:server:staging": ""}}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_server(task, config)
    else:
        assert expected == get_task_server(task, config)


# get_task_action {{{1
@pytest.mark.parametrize(
    "scopes,expected,raises",
    (
        (["project:releng:bouncer:action:submission", "project:releng:bouncer:action:aliases"], None, True),
        (["project:releng:bouncer:action:invalid"], None, True),
        (["project:releng:bouncer:action:submission"], "submission", False),
        (["project:releng:bouncer:action:aliases"], "aliases", False),
    ),
)
def test_get_task_action(scopes, expected, raises):
    task = {"scopes": scopes}
    config = {"taskcluster_scope_prefix": "project:releng:bouncer:", "schema_files": {"submission": "/some/path.json", "aliases": "/some/other_path.json"}}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_action(task, config)
    else:
        assert expected == get_task_action(task, config)


# get_supported_actions {{{1
def test_get_supported_actions():
    config = {"schema_files": {"submission": "/some/path.json", "aliases": "/some/other_path.json"}}
    assert sorted(get_supported_actions(config)) == sorted(("submission", "aliases"))


# validate_task_schema {{{1
def test_validate_task_schema(submission_context, schema="submission"):
    validate_task_schema(submission_context)


# check_product_names_match_aliases {{{1
@pytest.mark.parametrize(
    "entries,raises",
    (
        ({"firefox-devedition-latest": "Devedition-70.0b2"}, False),
        ({"firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL"}, False),
        ({"firefox-devedition-stub": "Devedition-70.0b2-stub"}, False),
        ({"firefox-devedition-latest": "Devedition-70.0"}, True),
        ({"firefox-devedition-latest-ssl": "Devedition-70.0.1-SSL"}, True),
        ({"firefox-devedition-stub": "Devedition-70.0-stub"}, True),
        ({"firefox-devedition-latest": "Devedition-70.0b2", "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL", "firefox-devedition-stub": "Devedition-70.0b2-stub"}, False),
        (
            {
                "firefox-devedition-latest": "Devedition-70.0b2",
                "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL",
                "firefox-devedition-msi-latest-ssl": "Devedition-70.0b2-msi-SSL",
                "firefox-devedition-msix-latest-ssl": "Devedition-70.0b2-msix-SSL",
                "firefox-devedition-stub": "Devedition-70.0b2-stub",
            },
            False,
        ),
        ({"firefox-devedition-latest": "Devedition-70.0b2", "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL", "firefox-devedition-stub": "Devedition-70.0-stub"}, True),
        ({"firefox-devedition-latest": "Devedition-70.02", "firefox-devedition-latest-ssl": "Devedition-70.0b2-SSL", "firefox-devedition-stub": "Devedition-70.0.1-stub"}, True),
        ({"firefox-beta-latest": "Firefox-70.0b2"}, False),
        ({"firefox-beta-latest-ssl": "Firefox-70.0b2-SSL"}, False),
        ({"firefox-beta-msi-latest-ssl": "Firefox-70.0b2-msi-SSL"}, False),
        ({"firefox-beta-msix-latest-ssl": "Firefox-70.0b2-msix-SSL"}, False),
        ({"firefox-beta-pkg-latest-ssl": "Firefox-70.0b2-pkg-SSL"}, False),
        ({"firefox-beta-stub": "Firefox-70.0b2-stub"}, False),
        ({"firefox-beta-latest": "Firefox-70.0"}, True),
        ({"firefox-beta-latest-ssl": "Firefox-70.0.1-SSL"}, True),
        ({"firefox-beta-stub": "Firefox-70.0-stub"}, True),
        ({"firefox-beta-latest": "Firefox-70.0b2", "firefox-beta-latest-ssl": "Firefox-70.0b2-SSL", "firefox-beta-stub": "Firefox-70.0b2-stub"}, False),
        ({"firefox-beta-latest": "Firefox-70.0b2", "firefox-beta-latest-ssl": "Firefox-70.0b2-SSL", "firefox-beta-stub": "Firefox-70.0-stub"}, True),
        ({"firefox-beta-latest": "Firefox-70.02", "firefox-beta-latest-ssl": "Firefox-70.0b2-SSL", "firefox-beta-stub": "Firefox-70.0.1-stub"}, True),
        ({"firefox-latest": "Firefox-70.0"}, False),
        ({"firefox-latest-ssl": "Firefox-70.0.1-SSL"}, False),
        ({"firefox-stub": "Firefox-70.0.2-stub"}, False),
        ({"firefox-latest": "Firefox-70.0b1"}, True),
        ({"firefox-latest-ssl": "Firefox-70.0b1-SSL"}, True),
        ({"firefox-stub": "Firefox-70-stub"}, True),
        ({"firefox-latest": "Firefox-70.0", "firefox-latest-ssl": "Firefox-70.0-SSL", "firefox-stub": "Firefox-70.0-stub"}, False),
        ({"firefox-latest": "Firefox-70.0", "firefox-latest-ssl": "Firefox-70.0-SSL", "firefox-stub": "Firefox-70-stub"}, True),
        ({"firefox-latest": "Firefox-70.02", "firefox-latest-ssl": "Firefox-70.0b2-SSL", "firefox-stub": "Firefox-70-stub"}, True),
        ({"firefox-latest-ssl": "Firefox-59.0b14-SSL", "firefox-latest": "Firefox-59.0b14", "firefox-stub": "Firefox-59.0b14-stub"}, True),
        ({"firefox-esr-latest": "Firefox-70.1.0esr"}, False),
        ({"firefox-esr-latest-ssl": "Firefox-70.1.2esr-SSL"}, False),
        ({"firefox-esr-latest": "Firefox-70.2.1"}, True),
        ({"firefox-esr-latest-ssl": "Firefox-70.0b1-SSL"}, True),
        ({"firefox-esr-latest": "Firefox-70.1.0esr", "firefox-esr-latest-ssl": "Firefox-70.1.2esr-SSL"}, False),
        ({"firefox-esr-next-latest": "Firefox-70.1.0esr", "firefox-esr-next-latest-ssl": "Firefox-70.1.2esr-SSL"}, False),
        ({"firefox-esr-latest": "Firefox-70.1.0esr", "firefox-esr-latest-ssl": "Firefox-70.1.2-SSL"}, True),
        ({"firefox-esr-latest": "Firefox-70.1.0esr", "firefox-esr-latest-ssl": "Firefox-70.0b1-SSL"}, True),
        ({"firefox-sha1": "Firefox-52.7.2esr-sha1"}, False),
        ({"firefox-sha1-ssl": "Firefox-52.7.2esr-sha1"}, False),
        ({"firefox-sha1": "Firefox-70.1.0esr"}, True),
        ({"firefox-sha1-ssl": "Firefox-70.1.2esr"}, True),
        ({"firefox-sha1": "Firefox-52.7.2esr-sha1", "firefox-sha1-ssl": "Firefox-70.1.2esr-sha1"}, False),
        ({"firefox-sha1": "Firefox-70.1.0esr", "firefox-sha1-ssl": "Firefox-70.1.2-sha1"}, True),
        ({"firefox-sha1": "Firefox-70.1.0esr", "firefox-sha1-ssl": "Firefox-70.1.2esr-sha1"}, True),
        ({"thunderbird-beta-latest": "Thunderbird-70.0b2"}, False),
        ({"thunderbird-beta-latest-ssl": "Thunderbird-70.0b2-SSL"}, False),
        ({"thunderbird-beta-msi-latest-ssl": "Thunderbird-70.0b2-msi-SSL"}, False),
        ({"thunderbird-latest": "Thunderbird-60.6.1"}, False),
        ({"thunderbird-latest-ssl": "Thunderbird-60.6.1-SSL"}, False),
        ({"thunderbird-msi-latest-ssl": "Thunderbird-60.6.1-msi-SSL"}, False),
        ({"Thunderbird-beta-latest": "Thunderbird-70.0"}, True),
        ({"Thunderbird-beta-latest-ssl": "Thunderbird-70.0.1-SSL"}, True),
        ({"thunderbird-beta-msi-latest-ssl": "Thunderbird-60.6.1-msi-SSL"}, True),
        ({"thunderbird-latest": "Thunderbird-70.0b1"}, True),
        ({"thunderbird-latest-ssl": "Thunderbird-70.0b1-SSL"}, True),
        ({"thunderbird-msi-latest-ssl": "Thunderbird-70.0b1-msi-SSL"}, True),
        ({"partner-firefox-beta-foo-bar-baz-latest": "Firefox-69.0b9-foo-bar-baz", "partner-firefox-beta-foo-bar-baz-stub": "Firefox-69.0b9-foo-bar-baz-stub"}, False),
        ({"partner-firefox-release-foo-bar-baz-latest": "Firefox-69.0-foo-bar-baz", "partner-firefox-release-foo-bar-baz-stub": "Firefox-69.0-foo-bar-baz-stub"}, False),
        ({"partner-firefox-release-foo-bar-baz-latest": "Firefox-69.0.1-foo-bar-baz", "partner-firefox-release-foo-bar-baz-stub": "Firefox-69.0.1-foo-bar-baz-stub"}, False),
        ({"partner-firefox-esr-foo-bar-baz-latest": "Firefox-68.0esr-foo-bar-baz", "partner-firefox-esr-foo-bar-baz-stub": "Firefox-68.0esr-foo-bar-baz-stub"}, False),
        ({"partner-firefox-esr-foo-bar-baz-latest": "Firefox-68.0.2esr-foo-bar-baz", "partner-firefox-esr-foo-bar-baz-stub": "Firefox-68.0.2esr-foo-bar-baz-stub"}, False),
        ({"partner-firefox-beta-foo-bar-baz-latest": "Firefox-69.0b9", "partner-firefox-beta-foo-bar-baz-stub": "Firefox-69.0b9-stub"}, True),
        ({"firefox-latest": "Firefox-69.0b9-foo-bar-baz", "firefox-stub": "Firefox-69.0b9-foo-bar-baz-stub"}, True),
        ({"corrupt-alias": "corrupt-entry"}, True),
    ),
)
def test_check_product_names_match_aliases(aliases_context, entries, raises):
    context = aliases_context
    context.task["payload"]["aliases_entries"] = entries
    if raises:
        with pytest.raises(TaskVerificationError):
            check_product_names_match_aliases(context)
    else:
        check_product_names_match_aliases(context)


# check_locations_match {{{1
@pytest.mark.parametrize(
    "locations, product_config, raises",
    (
        (["a", "b"], {"aaaa": "a", "bbbb": "b"}, False),
        (["a", "b"], {"aaaa": "b", "bbbb": "a"}, False),
        ([], {}, False),
        (["a"], {"a": "b"}, True),
        ([], {"a": "b"}, True),
    ),
)
def test_check_locations_match(locations, product_config, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_locations_match(locations, product_config)
    else:
        check_locations_match(locations, product_config)


# check_path_matches_destination {{{1
@pytest.mark.parametrize(
    "product_name, path, raises",
    (
        (
            ("Firefox-61.0b15-SSL", "/firefox/releases/61.0b15/mac/:lang/Firefox%2061.0b15.dmg", False),
            ("Firefox-61.0b15", "/firefox/releases/61.0b15/linux-x86_64/:lang/firefox-61.0b15.tar.bz2", False),
            ("Firefox-61.0b15", "/firefox/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe", False),
            ("Firefox-65.0b13-msi-SSL", "/firefox/releases/65.0b13/win64/:lang/Firefox%20Setup%2065.0b13.msi", False),
            ("Firefox-65.0b13-msix-SSL", "/firefox/releases/65.0b13/win64/:lang/Firefox%20Setup%2065.0b13.msix", False),
            ("Firefox-65.0b13-pkg-SSL", "/firefox/releases/65.0b13/mac/:lang/Firefox%2065.0b13.pkg", False),
            ("Devedition-65.0b13-msi-SSL", "/devedition/releases/65.0b13/win64/:lang/Firefox%20Setup%2065.0b13.msi", False),
            ("Devedition-65.0b13-msix-SSL", "/devedition/releases/65.0b13/win64/:lang/Firefox%20Setup%2065.0b13.msix", False),
            ("Thunderbird-65.0b13-msi-SSL", "/firefox/releases/65.0b13/win64/:lang/Thunderbird%20Setup%2065.0b13.msi", True),
            ("Firefox-65.0b13-pkg-SSL", "/firefox/releases/65.0b13/win64/:lang/Firefox%20Setup%2065.0b13.pkg", False),
            ("Firefox-61.0b15", "/firefox/releases/61.0b15/mac/:lang/Firefox%2061.0b15.dmg", False),
            ("Firefox-61.0b15", "/devedition/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe", True),
            ("Firefox-61.0b15-Complete", "/firefox/releases/61.0b15/update/win64/:lang/firefox-61.0b15.complete.mar", False),
            ("Firefox-61.0b15-Complete", "/firefox/releases/61.0b15/update/linux-i686/:lang/firefox-61.0b15.complete.mar", False),
            ("Firefox-61.0b15-Complete", "/firefox/releases/61.0b15/update/mac/:lang/firefox-61.0b15.complete.marx", True),
            ("Firefox-61.0b15-Partial-61.0b15", "/firefox/releases/61.0b15/update/linux-x86_64/:lang/firefox-61.0b15-61.0b15.partial.mar", False),
            ("Firefox-61.0b15-Partial-61.0b15", "/firefox/releases/61.0b15/update/win64/:lang/firefox-61.0b15-61.0b15.partial.mar", False),
            ("Firefox-61.0b15-SSL", "/firefox/releases/61.0b15/linux-i686/:lang/firefox-61.0b15.tar.bz2", False),
            ("Firefox-61.0b15-SSL", "/firefox/releases/61.0b15/win64/Firefox%20Setup%2061.0b15.exe", True),
            ("Firefox-61.0b15-SSL", "/firefox/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe", False),
            ("Firefox-61.0b15-stub", "/firefox/releases/61.0b15/win32/:lang/Firefox%20Installer.exe", False),
            ("Firefox-61.0b15-stub", "/firefox/releases/61.0b15/win32/:lang/Firefox%20Installer.exe", False),
            ("Firefox-61.0b15-stub", "/mobile/releases/61.0b15/win32/:lang/Firefox%20Installer.exe", True),
            ("Firefox-62.0build1-Partial-60.0.2build1", "/firefox/candidates/62.0-candidates/build1/update/linux-i686/:lang/firefox-60.0.2-62.0.partial.mar", False),
            ("Firefox-62.0build1-Partial-60.0.2build1", "/firefox/releases/62.0/update/linux-i686/:lang/firefox-60.0.2-62.0.partial.mar", True),
            ("Devedition-61.0b15", "/devedition/releases/61.0b15/linux-i686/:lang/firefox-61.0b15.tar.bz2", False),
            ("Devedition-61.0b15", "/firefox/releases/61.0b15/linux-x86_64/:lang/firefox-61.0b15.tar.bz2", True),
            ("Devedition-61.0b15-Complete", "/devedition/releases/61.0b15/update/mac/:lang/firefox-61.0b15.complete.mar", False),
            ("Devedition-61.0b15-Complete", "/devedition/releases/61.0b15/:lang/firefox-61.0b15.complete.mar", True),
            ("Devedition-61.0b15-Partial-61.0b15", "/devedition/releases/update/win32/:lang/firefox-61.0b15-61.0b15.partial.mar", False),
            ("Devedition-61.0b15-Partial-61.0b15", "/devedition/releases/update/lang/firefox-61.0b15-61.0b15.partial.mar", True),
            ("Devedition-61.0b15-SSL", "/devedition/releases/61.0b15/linux-i686/:lang/firefox-61.0b15.tar.bz2", False),
            ("Devedition-61.0b15-SSL", "/devedition/releases/61.0b15/win64/:lang/Devedition%20Setup%2061.0b15.exe", True),
            ("Devedition-61.0b15-SSL", "/devedition/releases/61.0b15/win64/:lang/Firefox%20Setup%2061.0b15.exe", False),
            ("Devedition-61.0b15-stub", "/devedition/releases/61.0b15/win32/:lang/Firefox%20Installer.exe", False),
            ("Devedition-61.0b15-stub", "/devedition/releases/61.0b15/win32/:lang/Firefox%20Installer.exe", False),
            ("Devedition-61.0b15-stub", "/devedition/candidates/61.0b15/win32/:lang/Firefox%20Installer.exe", True),
            ("Thunderbird-62.0b7", "/thunderbird/releases/62.0b7/mac/:lang/Thunderbird%2062.0b7.dmg", False),
            ("Thunderbird-62.0b7", "/firefox/releases/62.0b7/win32/:lang/Thunderbird%20Setup%2062.0b7.exe", True),
            ("Thunderbird-62.0b7-Complete", "/thunderbird/releases/62.0b7/update/mac/:lang/thunderbird-62.0b7.complete.mar", False),
            ("Thunderbird-62.0b7-Complete", "/thunderbird/releases/62.0b7/update/linux-x86_64/:lang/thunderbird-62.0b7.complete.mar", False),
            ("Thunderbird-62.0b7-Complete", "/thunderbird/releases/62.0b7/update/win64/:lang/thunderbird-62.0b7.complete.mar", False),
            ("Thunderbird-62.0b7-Complete", "/thunderbird/releases/62.0b7/update/win64/:lang/thunderbird-62.0b7.complete.partial", True),
            ("Thunderbird-62.0b7-SSL", "/thunderbird/releases/62.0b7/win64/:lang/Thunderbird%20Setup%2062.0b7.exe", False),
            ("Thunderbird-67.0b2-msi-SSL", "/thunderbird/releases/67.0b2/win64/:lang/Thunderbird%20Setup%2067.0b2.msi", False),
            ("Thunderbird-62.0b7-SSL", "/thunderbird/releases/62.0b7/mac/:lang/Thunderbird%2062.0b7.dmg", False),
            ("Thunderbird-62.0b7-SSL", "/thunderbird/releases/62.0b7/linux-i686/:lang/thunderbird-62.0b7.tar.bz2", False),
            ("Thunderbird-62.0b7-SSL", "/thunderbird/candidates/62.0b7/linux-x86_64/:lang/thunderbird-62.0b7.tar.bz2", True),
        )
    ),
)
def test_check_path_matches_destination(product_name, path, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_path_matches_destination(product_name, path)
    else:
        check_path_matches_destination(product_name, path)


# check_aliases_match {{{1
@pytest.mark.parametrize(
    "entries,provided,raises",
    (
        (
            (
                {"firefox-latest": "Firefox-61.0.1", "firefox-latest-ssl": "Firefox-61.0.1-SSL", "firefox-stub": "Firefox-61.0.1-stub"},
                {
                    ("https://download.mozilla.org/?product=" "firefox-latest&print=yes"): (
                        "https://download-installer.cdn." "mozilla.net/pub/firefox/releases/" "61.0.1/win32/en-US/Firefox%20Setup" "%2061.0.1.exe"
                    ),
                    ("https://download.mozilla.org/?product=" "firefox-latest-ssl&print=yes"): (
                        "https://download-installer.cdn." "mozilla.net/pub/firefox/releases/" "61.0.1/win32/en-US/Firefox%20Setup" "%2061.0.1.exe"
                    ),
                    ("https://download.mozilla.org/?product=" "firefox-stub&print=yes"): (
                        "https://download-installer.cdn.mozilla." "net/pub/firefox/releases/61.0.1/win32/" "en-US/Firefox%20Installer.exe"
                    ),
                    ("https://download.mozilla.org/?product=" "Firefox-61.0.1&print=yes"): (
                        "https://download-installer.cdn.mozilla." "net/pub/firefox/releases/61.0.1/win32/" "en-US/Firefox%20Setup%2061.0.1.exe"
                    ),
                    ("https://download.mozilla.org/?product=" "Firefox-61.0.1-SSL&print=yes"): (
                        "https://download-installer.cdn." "mozilla.net/pub/firefox/releases/" "61.0.1/win32/en-US/Firefox%20Setup" "%2061.0.1.exe"
                    ),
                    ("https://download.mozilla.org/?product=" "Firefox-61.0.1-stub&print=yes"): (
                        "https://download-installer.cdn." "mozilla.net/pub/firefox/releases/" "61.0.1/win32/en-US/Firefox%20Installer.exe"
                    ),
                },
                False,
            ),
            (
                {"thunderbird-next-latest": "Thunderbird-62.0", "thunderbird-next-latest-ssl": "Thunderbird-62.0", "thunderbird-latest-ssl": "Thunderbird-62.0"},
                {
                    ("https://download.mozilla.org/?product=" "thunderbird-next-latest-ssl&print=yes"): "404 page not found\n",
                    ("https://download.mozilla.org/?product=" "thunderbird-next-latest&print=yes"): "404 page not found\n",
                    ("https://download.mozilla.org/?product=" "thunderbird-latest-ssl&print=yes"): "404 page not found\n",
                },
                False,
            ),
            (
                {"firefox-latest": "Firefox-61.0.1"},
                {
                    ("https://download.mozilla.org/?product=" "firefox-latest&print=yes"): (
                        "https://download-installer.cdn." "mozilla.net/pub/firefox/releases/" "61.0/win32/en-US/Firefox%20Setup" "%2061.0.1.exe"
                    ),
                    ("https://download.mozilla.org/?product=" "Firefox-61.0.1&print=yes"): (
                        "https://download-installer.cdn.mozilla." "net/pub/firefox/releases/61.0.1/win32/" "en-US/Firefox%20Setup%2061.0.1.exe"
                    ),
                },
                True,
            ),
        )
    ),
)
@pytest.mark.asyncio
async def test_check_aliases_match(aliases_context, mocker, entries, provided, raises):
    async def fake_retry_request(context, url, good=(200,)):
        return provided[url]

    aliases_context.task["payload"]["aliases_entries"] = entries
    mocker.patch.object(btask, "retry_request", new=fake_retry_request)

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            await check_aliases_match(aliases_context)
    else:
        await check_aliases_match(aliases_context)


# check_product_names_match_nightly_locations {{{1
@pytest.mark.parametrize(
    "products,raises",
    (
        (
            (["firefox-nightly-latest", "firefox-nightly-latest-ssl", "firefox-nightly-latest-l10n", "firefox-nightly-latest-l10n-ssl"], False),
            (["firefox-nightly-msi-latest-ssl", "firefox-nightly-msi-latest-l10n-ssl"], True),
            (["firefox-nightly-pkg-latest-ssl", "firefox-nightly-pkg-latest-l10n-ssl"], True),
            (["firefox-nightly-msi-latest-ssl", "firefox-nightly-msi-latest-l10n-ssl", "firefox-nightly-latest"], True),
            (["firefox-nightly-pkg-latest-ssl", "firefox-nightly-pkg-latest-l10n-ssl", "firefox-nightly-latest"], True),
            (["firefox-nightly-msi-latest-l10n-ssl", "firefox-nightly-latest"], True),
            (["firefox-nightly-pkg-latest-l10n-ssl", "firefox-nightly-latest"], True),
            (
                [
                    "firefox-nightly-msi-latest-ssl",
                    "firefox-nightly-msi-latest-l10n-ssl",
                    "firefox-nightly-pkg-latest-ssl",
                    "firefox-nightly-pkg-latest-l10n-ssl",
                    "firefox-nightly-latest",
                    "firefox-nightly-latest-ssl",
                    "firefox-nightly-latest-l10n",
                    "firefox-nightly-latest-l10n-ssl",
                ],
                False,
            ),
            (
                [
                    "firefox-nightly-msi-latest-ssl",
                    "firefox-nightly-msi-latest-l10n-ssl",
                    "firefox-nightly-msix-latest-ssl",
                    "firefox-nightly-pkg-latest-ssl",
                    "firefox-nightly-pkg-latest-l10n-ssl",
                    "firefox-nightly-latest",
                    "firefox-nightly-latest-ssl",
                    "firefox-nightly-latest-l10n",
                    "firefox-nightly-latest-l10n-ssl",
                ],
                False,
            ),
            (["firefox-nightly-latest-l10n", "firefox-nightly-latest-l10n-ssl", "Firefox-64"], True),
            (["firefox-nightly-latest", "firefox-nightly-latest-ssl"], True),
            (["firefox-nightly-latest-l10n", "firefox-nightly-latest-l10n-ssl"], True),
            (["firefox-latest"], True),
            (["thunderbird-nightly-latest", "thunderbird-nightly-latest-ssl", "thunderbird-nightly-latest-l10n", "thunderbird-nightly-latest-l10n-ssl"], True),
            (["thunderbird-nightly-msi-latest-ssl", "thunderbird-nightly-msi-latest-l10n-ssl"], True),
            (["thunderbird-nightly-pkg-latest-ssl", "thunderbird-nightly-pkg-latest-l10n-ssl"], True),
            (["thunderbird-nightly-msi-latest-ssl", "thunderbird-nightly-msi-latest-l10n-ssl", "thunderbird-nightly-latest"], True),
            (["thunderbird-nightly-pkg-latest-ssl", "thunderbird-nightly-pkg-latest-l10n-ssl", "thunderbird-nightly-latest"], True),
            (["thunderbird-nightly-msi-latest-l10n-ssl", "thunderbird-nightly-latest"], True),
            (["thunderbird-nightly-pkg-latest-l10n-ssl", "thunderbird-nightly-latest"], True),
            (
                [
                    "thunderbird-nightly-msi-latest-ssl",
                    "thunderbird-nightly-msi-latest-l10n-ssl",
                    "thunderbird-nightly-pkg-latest-ssl",
                    "thunderbird-nightly-pkg-latest-l10n-ssl",
                    "thunderbird-nightly-latest",
                    "thunderbird-nightly-latest-ssl",
                    "thunderbird-nightly-latest-l10n",
                    "thunderbird-nightly-latest-l10n-ssl",
                ],
                False,
            ),
        )
    ),
)
def test_check_product_names_match_nightly_locations(locations_context, products, raises):
    locations_context.task["payload"]["bouncer_products"] = products
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_product_names_match_nightly_locations(locations_context)
    else:
        check_product_names_match_nightly_locations(locations_context)


# check_version_matches_nightly_regex {{{1
@pytest.mark.parametrize(
    "version,product,raises",
    (
        (
            ("63.0a1", "firefox", (False, None)),
            ("63.0b1", "firefox", (True, ScriptWorkerTaskException)),
            ("63.0.1a1", "firefox", (True, PatternNotMatchedError)),
            ("63.0.1esr", "firefox", (True, PatternNotMatchedError)),
            ("63.0.1", "firefox", (True, ScriptWorkerTaskException)),
            ("63.0", "firefox", (True, ScriptWorkerTaskException)),
            ("ZFJSh389fjSMN<@<Ngv", "firefox", (True, PatternNotMatchedError)),
            ("63", "firefox", (True, PatternNotMatchedError)),
            ("76.0a1", "thunderbird", (False, None)),
            ("76.0b1", "thunderbird", (True, ScriptWorkerTaskException)),
            ("76.0.1a1", "thunderbird", (True, PatternNotMatchedError)),
            ("76.0.1esr", "thunderbird", (True, PatternNotMatchedError)),
            ("76.0.1", "thunderbird", (True, ScriptWorkerTaskException)),
            ("76.0", "thunderbird", (True, ScriptWorkerTaskException)),
            ("ZFJSh389fjSMN<@<Ngv", "thunderbird", (True, PatternNotMatchedError)),
            ("76", "thunderbird", (True, PatternNotMatchedError)),
        )
    ),
)
def test_check_version_matches_nightly_regex(version, product, raises):
    if raises[0]:
        with pytest.raises(raises[1]):
            check_version_matches_nightly_regex(version, product)
    else:
        check_version_matches_nightly_regex(version, product)


# check_location_path_matches_destination {{{1
@pytest.mark.parametrize(
    "product_name,path,raises",
    (
        (
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.bz2", False),
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-x86_64.tar.bz2", False),
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win64-aarch64.installer.exe", False),
            ("firefox-nightly-msi-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win64.installer.msi", False),
            ("firefox-nightly-msi-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win64.installer.msi", False),
            ("firefox-nightly-msi-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.msi", False),
            ("firefox-nightly-msi-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win64.installer.exe", True),
            ("firefox-nightly-msi-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.nac.installer.msi", True),
            ("firefox-nightly-pkg-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.mac.pkg", False),
            ("firefox-nightly-pkg-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.mac.pkg", False),
            ("firefox-nightly-pkg-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.mac.pkg", False),
            ("firefox-nightly-pkg-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.mac.msi", True),
            ("firefox-nightly-pkg-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.nac.pkg", True),
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.mac.dmg", False),
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win64.installer.exe", False),
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exe", False),
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exeexe", True),
            ("firefox-nightly-latest", "/firefox/candidates/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exeexe", True),
            ("firefox-nightly-latest", "/mobile/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exeexe", True),
            ("firefox-nightly-latest", "/mobile/nightly/latest-mozilla-central/firefox-63.0a1.:lang.win32.installer.exeexe", True),
            ("firefox-nightly-latest", "/mobile/nightly/latest-mozilla-central/firefox-63.0b1.:lang.win32.installer.exeexe", True),
            ("firefox-nightly-latest", "/devedition/releases/latest-mozilla-central-l10n/firefox-63.0a1.:lang.mac.dmg", True),
            ("firefox-nightly-latest", "/devedition/releases/latest-mozilla-central/firefox-63.0a1.:lang.mac.dmg", True),
            ("firefox-nightly-latest", "/devedition/releases/latest-mozilla-central/firefox-63.0b1.:lang.mac.dmg", True),
            ("firefox-nightly-latest", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.gz", True),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win64.installer.exe", False),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.mac.dmg", False),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-x86_64.tar.bz2", False),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.bz2", False),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exe", False),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win64-aarch64.installer.exe", False),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/candidates/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exe", True),
            ("firefox-nightly-latest-l10n-ssl", "/mobile/releases/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exe", True),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0b1.:lang.win32.installer.exe", True),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0.1.:lang.win64.installer.exe", True),
            ("firefox-nightly-latest-l10n-ssl", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0.:lang.mac.dmg", True),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win32.installer.exe", False),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win64.installer.exe", False),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-66.0a1.en-US.win64-aarch64.installer.exe", False),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.mac.dmg", False),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.linux-x86_64.tar.bz2", False),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0a1.en-US.linux-i686.tar.bz2", False),
            ("firefox-nightly-latest-ssl", "/mobile/nightly/latest-mozilla-central/firefox-63.0a1.en-US.win32.installer.exe", True),
            ("firefox-nightly-latest-ssl", "/firefox/candidates/latest-mozilla-central/firefox-63.0a1.en-US.win64.installer.exe", True),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0b1.en-US.mac.dmg", True),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0.1.en-US.linux-x86_64.tar.bz2", True),
            ("firefox-nightly-latest-ssl", "/firefox/nightly/latest-mozilla-central/firefox-63.0.en-US.linux-i686.tar.bz2", True),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exe", False),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.bz2", False),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-66.0a1.:lang.win64-aarch64.installer.exe", False),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-x86_64.tar.bz2", False),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.mac.dmg", False),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win64.installer.exe", False),
            ("firefox-nightly-latest-l10n", "/mobile/nightly/latest-mozilla-central-l10n/firefox-63.0a1.:lang.win32.installer.exe", True),
            ("firefox-nightly-latest-l10n", "/firefox/candidates/latest-mozilla-central-l10n/firefox-63.0a1.:lang.linux-i686.tar.bz2", True),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0b1.:lang.linux-x86_64.tar.bz2", True),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0b1.:lang.mac.dmg", True),
            ("firefox-nightly-latest-l10n", "/firefox/nightly/latest-mozilla-central-l10n/firefox-63.0.1.:lang.win64.installer.exe", True),
            ("thunderbird-nightly-latest", "/thunderbird/nightly/latest-comm-central/thunderbird-63.0a1.en-US.linux-x86_64.tar.bz2", False),
            ("thunderbird-nightly-msi-latest-l10n-ssl", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0a1.:lang.win64.installer.exe", True),
            ("thunderbird-nightly-latest-l10n", "/thunderbird/nightly/latest-comm-central-l10n/thunderbird-63.0a1.:lang.win32.installer.exe", False),
            ("thunderbird-nightly-latest-l10n", "/thunderbird/candidates/latest-comm-central-l10n/thunderbird-63.0a1.:lang.win32.installer.exeexe", True),
            ("thunderbird-nightly-latest-l10n", "/mobile/nightly/latest-comm-central-l10n/thunderbird-63.0a1.:lang.win32.installer.exeexe", True),
        )
    ),
)
def test_check_location_path_matches_destination(product_name, path, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_location_path_matches_destination(product_name, path)
    else:
        check_location_path_matches_destination(product_name, path)


# check_versions_are_successive {{{1
@pytest.mark.parametrize(
    "current_version,payload_version,product,raises",
    (
        (
            ("63.0a1", "64.0a1", "firefox", False),
            ("63.0a1", "63.0a1", "firefox", True),
            ("63.0a1", "65.0a1", "firefox", True),
            ("64.0a1", "63.0a1", "firefox", True),
            ("68.2a1", "68.1a1", "VNSJKSGH#(*#HG#LG@()", True),
            ("75.0a1", "76.0a1", "thunderbird", False),
            ("75.0a1", "75.0a1", "thunderbird", True),
            ("75.0a1", "77.0a1", "thunderbird", True),
            ("76.0a1", "75.0a1", "thunderbird", True),
            ("78.2a1", "78.1a1", "VNSJKSGH#(*#HG#LG@()", True),
        )
    ),
)
def test_check_versions_are_successive(current_version, payload_version, product, raises):
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            check_versions_are_successive(current_version, payload_version, product)
    else:
        check_versions_are_successive(current_version, payload_version, product)
