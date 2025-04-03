import pytest

from landoscript.script import async_main
from tests.conftest import assert_add_commit_response, assert_lando_submission_response, assert_status_response, setup_fetch_files_response, setup_fetch_files_responses, setup_test


/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/pytest_asyncio/plugin.py:207: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Valid fixture loop scopes are: "function", "class", "module", "package", "session"

  warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
======================================================================================= test session starts =======================================================================================
platform linux -- Python 3.11.6, pytest-8.3.5, pluggy-1.5.0
rootdir: /mnt/data/repos/scriptworker-scripts
configfile: setup.cfg
plugins: cov-6.0.0, aioresponses-0.3.0, anyio-4.9.0, scriptworker-client-0.1.0, xdist-3.6.1, asyncio-0.25.3
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None
collected 4 items                                                                                                                                                                                 

tests/test_android_l10n_import.py FFFF                                                                                                                                                      [100%]

============================================================================================ FAILURES =============================================================================================
______________________________________________________________________________________ test_success[import] _______________________________________________________________________________________
tests/test_android_l10n_import.py:253: in test_success
    await async_main(context)
src/landoscript/script.py:103: in async_main
    import_action = await android_l10n_import.run(
src/landoscript/actions/android_l10n_import.py:50: in run
    diff_contents(src_files[fn], dst_files[fn], fn)
E   KeyError: 'mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml'
-------------------------------------------------------------------------------------- Captured stdout call ---------------------------------------------------------------------------------------
Creating list of files for locale: my.
Creating list of files for locale: zam.
Creating list of files for locale: ab.
_____________________________________________________________________________________ test_success[new files] _____________________________________________________________________________________
tests/test_android_l10n_import.py:253: in test_success
    await async_main(context)
src/landoscript/script.py:103: in async_main
    import_action = await android_l10n_import.run(
src/landoscript/actions/android_l10n_import.py:45: in run
    dst_files = await github_client.get_files(dst_repo_files)
/home/bhearsum/repos/scriptworker-scripts/scriptworker_client/src/scriptworker_client/github_client.py:139: in get_files
    contents = (await self._client.execute(str_query))["repository"]
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/simple_github/client.py:351: in execute
    return await session.execute(gql(query), variable_values=variables)
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1629: in execute
    result = await self._execute(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1819: in _execute
    return await self._execute_with_retries(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/backoff/_async.py:151: in retry
    ret = await target(*args, **kwargs)
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1792: in _execute_once
    answer = await super()._execute(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1538: in _execute
    result = await self.transport.execute(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/transport/aiohttp.py:332: in execute
    async with self.session.post(self.url, ssl=self.ssl, **post_args) as resp:
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/aiohttp/client.py:1425: in __aenter__
    self._resp: _RetType = await self._coro
/home/bhearsum/.pyenv/versions/3.11.6/lib/python3.11/unittest/mock.py:2248: in _execute_mock_call
    result = await effect(*args, **kwargs)
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/aioresponses/core.py:538: in _request_mock
    raise ClientConnectionError(
E   aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql
-------------------------------------------------------------------------------------- Captured stdout call ---------------------------------------------------------------------------------------
Creating list of files for locale: my.
Creating list of files for locale: zam.
Creating list of files for locale: ab.
---------------------------------------------------------------------------------------- Captured log call ----------------------------------------------------------------------------------------
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 0.7s (gql.transport.exceptions.TransportProtocolError: Server did not return a GraphQL result: No "data" or "errors" keys in answer: {})
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 1.6s (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 3.7s (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 3.4s (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
ERROR    backoff:_common.py:120 Giving up _execute_once(...) after 5 tries (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
___________________________________________________________________________________ test_success[removed file] ____________________________________________________________________________________
tests/test_android_l10n_import.py:253: in test_success
    await async_main(context)
src/landoscript/script.py:103: in async_main
    import_action = await android_l10n_import.run(
src/landoscript/actions/android_l10n_import.py:45: in run
    dst_files = await github_client.get_files(dst_repo_files)
/home/bhearsum/repos/scriptworker-scripts/scriptworker_client/src/scriptworker_client/github_client.py:139: in get_files
    contents = (await self._client.execute(str_query))["repository"]
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/simple_github/client.py:351: in execute
    return await session.execute(gql(query), variable_values=variables)
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1629: in execute
    result = await self._execute(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1819: in _execute
    return await self._execute_with_retries(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/backoff/_async.py:151: in retry
    ret = await target(*args, **kwargs)
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1792: in _execute_once
    answer = await super()._execute(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/client.py:1538: in _execute
    result = await self.transport.execute(
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/transport/aiohttp.py:332: in execute
    async with self.session.post(self.url, ssl=self.ssl, **post_args) as resp:
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/aiohttp/client.py:1425: in __aenter__
    self._resp: _RetType = await self._coro
/home/bhearsum/.pyenv/versions/3.11.6/lib/python3.11/unittest/mock.py:2248: in _execute_mock_call
    result = await effect(*args, **kwargs)
/home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/aioresponses/core.py:538: in _request_mock
    raise ClientConnectionError(
E   aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql
-------------------------------------------------------------------------------------- Captured stdout call ---------------------------------------------------------------------------------------
Creating list of files for locale: my.
Creating list of files for locale: zam.
Creating list of files for locale: ab.
---------------------------------------------------------------------------------------- Captured log call ----------------------------------------------------------------------------------------
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 0.2s (gql.transport.exceptions.TransportProtocolError: Server did not return a GraphQL result: No "data" or "errors" keys in answer: {})
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 0.6s (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 0.1s (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 0.7s (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
INFO     backoff:_common.py:105 Backing off _execute_once(...) for 7.1s (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
ERROR    backoff:_common.py:120 Giving up _execute_once(...) after 5 tries (aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql)
____________________________________________________________________________________ test_success[no changes] _____________________________________________________________________________________
tests/test_android_l10n_import.py:257: in test_success
    assert_success(req, initial_values, expected_values)
tests/test_android_l10n_import.py:57: in assert_success
    assert_add_commit_response(action, ["Import translations from android-l10n"], initial_values, expected_bumps)
tests/conftest.py:210: in assert_add_commit_response
    assert msg in action["commitmsg"]
E   AssertionError: assert 'Import translations from android-l10n' in 'somtehing'
-------------------------------------------------------------------------------------- Captured stdout call ---------------------------------------------------------------------------------------
Creating list of files for locale: my.
Creating list of files for locale: zam.
Creating list of files for locale: ab.
{'actions': [{'action': 'create-commit',
              'author': 'Release Engineering Landoscript '
                        '<release+landoscript@mozilla.com>',
              'commitmsg': 'somtehing',
              'date': '2025-04-03T20:46:24.935493+00:00',
              'diff': ''}]}
======================================================================================== warnings summary =========================================================================================
landoscript/tests/test_android_l10n_import.py::test_success[import]
landoscript/tests/test_android_l10n_import.py::test_success[new files]
landoscript/tests/test_android_l10n_import.py::test_success[removed file]
landoscript/tests/test_android_l10n_import.py::test_success[no changes]
  /home/bhearsum/.pyenv/versions/3.11.6/envs/landoscript/lib/python3.11/site-packages/gql/transport/aiohttp.py:92: UserWarning: WARNING: By default, AIOHTTPTransport does not verify ssl certificates. This will be fixed in the next major version. You can set ssl=True to force the ssl certificate verification or ssl=False to disable this warning
    warnings.warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
===================================================================================== short test summary info =====================================================================================
FAILED tests/test_android_l10n_import.py::test_success[import] - KeyError: 'mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml'
FAILED tests/test_android_l10n_import.py::test_success[new files] - aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql
FAILED tests/test_android_l10n_import.py::test_success[removed file] - aiohttp.client_exceptions.ClientConnectionError: Connection refused: POST https://api.github.com/graphql
FAILED tests/test_android_l10n_import.py::test_success[no changes] - AssertionError: assert 'Import translations from android-l10n' in 'somtehing'



ac_l10n_toml = """
basepath = "."

locales = [
    "ab",
]

[env]

[[paths]]
  reference = "components/**/src/main/res/values/strings.xml"
  l10n = "components/**/src/main/res/values-{android_locale}/strings.xml"
"""

fenix_l10n_toml = """
basepath = "."

locales = [
    "my",
]

[env]

[[paths]]
  reference = "app/src/main/res/values/strings.xml"
  l10n = "app/src/main/res/values-{android_locale}/strings.xml"
"""

focus_l10n_toml = """
basepath = "."

locales = [
    "zam",
]

[env]

[[paths]]
  reference = "app/src/main/res/values/strings.xml"
  l10n = "app/src/main/res/values-{android_locale}/strings.xml"
"""


def assert_success(req, initial_values, expected_bumps):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]
    assert len(create_commit_actions) == 1
    action = create_commit_actions[0]

    assert_add_commit_response(action, ["Import translations from android-l10n"], initial_values, expected_bumps)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "android_l10n_import_info,android_l10n_values,initial_values,expected_values",
    (
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            id="import",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in android-l10n
                "mozilla-mobile/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mozilla-mobile/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mozilla-mobile/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            {},
            {
                # paths in gecko
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my expected contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam expected contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab expected contents",
            },
            id="new files",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {},
            {
                # paths in gecko
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {},
            id="removed file",
        ),
        pytest.param(
            {
                "from_repo_url": "https://github.com/mozilla-l10n/android-l10n",
                "toml_info": [
                    {
                        "dest_path": "mobile/android/fenix",
                        "toml_path": "mozilla-mobile/fenix/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/focus-android",
                        "toml_path": "mozilla-mobile/focus-android/l10n.toml",
                    },
                    {
                        "dest_path": "mobile/android/android-components",
                        "toml_path": "mozilla-mobile/android-components/l10n.toml",
                    },
                ],
            },
            {
                # paths in gecko
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            {
                # paths in gecko
                "mobile/android/fenix/app/src/main/res/values-my/strings.xml": "my initial contents",
                "mobile/android/focus-android/app/src/main/res/values-zam/strings.xml": "zam initial contents",
                "mobile/android/android-components/components/browser/toolbar/src/main/res/values-ab/strings.xml": "ab initial contents",
            },
            id="no changes",
        ),
        # TODO: many file changes, file changes from more than one app, locale added, locale removed
    ),
)
async def test_success(aioresponses, github_installation_responses, context, android_l10n_import_info, android_l10n_values, initial_values, expected_values):
    payload = {
        "actions": ["android_l10n_import"],
        "lando_repo": "repo_name",
        "android_l10n_import_info": android_l10n_import_info,
        "ignore_closed_tree": True,
    }
    # done here because setup_test sets up github_installation_response too soon...argh
    from yarl import URL
    lando_repo = payload["lando_repo"]
    lando_api = context.config["lando_api"]
    owner = context.config["lando_name_to_github_repo"][lando_repo]["owner"]
    submit_uri = URL(f"{lando_api}/api/v1/{lando_repo}")
    job_id = 12345
    status_uri = URL(f"{lando_api}/push/{job_id}")

    scopes = [f"project:releng:landoscript:repo:repo_name"]
    scopes.append(f"project:releng:landoscript:action:android_l10n_import")

    # submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["android_l10n_import"])
    github_installation_responses("mozilla-l10n")
    setup_fetch_files_responses(
        aioresponses,
        [
            # toml files needed before fetching anything else
            {
                "mozilla-mobile/fenix/l10n.toml": fenix_l10n_toml,
                "mozilla-mobile/focus-android/l10n.toml": focus_l10n_toml,
                "mozilla-mobile/android-components/l10n.toml": ac_l10n_toml,
            },
            android_l10n_values,
        ],
    )
    github_installation_responses(owner)
    setup_fetch_files_response(aioresponses, 200, initial_values)

    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "completed",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    if initial_values.values() != expected_values.values():
        req = assert_lando_submission_response(aioresponses.requests, submit_uri)
        assert_success(req, initial_values, expected_values)
        assert_status_response(aioresponses.requests, status_uri)
    else:
        assert ("POST", submit_uri) not in aioresponses.requests
        assert ("GET", status_uri) not in aioresponses.requests
