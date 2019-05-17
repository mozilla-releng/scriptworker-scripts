import asyncio
import base64
from contextlib import contextmanager
import os
import os.path
import pytest
import shutil
import subprocess
import tarfile
import zipfile

from scriptworker_client.utils import makedirs

from iscript.exceptions import IScriptError
import iscript.widevine as iwv


## helper constants, fixtures, functions {{{1
# TEST_CERT_TYPE = '{}cert:dep-signing'.format(DEFAULT_SCOPE_PREFIX)
#
#
# @pytest.fixture(scope='function')
# def task_defn():
#    return {
#        'provisionerId': 'meh',
#        'workerType': 'workertype',
#        'schedulerId': 'task-graph-scheduler',
#        'taskGroupId': 'some',
#        'routes': [],
#        'retries': 5,
#        'created': '2015-05-08T16:15:58.903Z',
#        'deadline': '2015-05-08T18:15:59.010Z',
#        'expires': '2016-05-08T18:15:59.010Z',
#        'dependencies': ['VALID_TASK_ID'],
#        'scopes': ['signing'],
#        'payload': {
#          'upstreamArtifacts': [{
#            'taskType': 'build',
#            'taskId': 'VALID_TASK_ID',
#            'formats': ['gpg'],
#            'paths': ['public/build/firefox-52.0a1.en-US.win64.installer.exe'],
#          }]
#        }
#    }
#
#
# @contextmanager
# def context_die(*args, **kwargs):
#    raise IScriptError("dying")
#
#
# def is_tarfile(archive):
#    try:
#        import tarfile
#        tarfile.open(archive)
#    except tarfile.ReadError:
#        return False
#    return True
#
#
# async def assert_file_permissions(archive):
#    with tarfile.open(archive, mode='r') as t:
#        for member in t.getmembers():
#            assert member.uid == 0
#            assert member.gid == 0
#
#
# async def helper_archive(context, filename, create_fn, extract_fn, *args):
#    tmpdir = context.config['artifact_dir']
#    archive = os.path.join(context.config['work_dir'], filename)
#    # Add a directory to tickle the tarfile isfile() call
#    files = [__file__, SERVER_CONFIG_PATH]
#    await create_fn(
#        context, archive, [__file__, SERVER_CONFIG_PATH], *args,
#        tmp_dir=BASE_DIR
#    )
#    # Not relevant for zip
#    if is_tarfile(archive):
#        await assert_file_permissions(archive)
#    await extract_fn(context, archive, *args, tmp_dir=tmpdir)
#    for path in files:
#        target_path = os.path.join(tmpdir, os.path.relpath(path, BASE_DIR))
#        assert os.path.exists(target_path)
#        assert os.path.isfile(target_path)
#        hash1 = get_hash(path)
#        hash2 = get_hash(target_path)
#        assert hash1 == hash2
#
#
## sign_file {{{1
# @pytest.mark.asyncio
# @pytest.mark.parametrize('to,expected', ((
#    None, 'from',
# ), (
#    'to', 'to'
# )))
# async def test_sign_file_cert_signing_server(context, mocker, to, expected):
#    context.task = {
#        'scopes': ['project:releng:signing:cert:dep-signing']
#    }
#    mocker.patch.object(sign, 'build_signtool_cmd', new=noop_sync)
#    mocker.patch.object(utils, 'execute_subprocess', new=noop_async)
#    assert await sign.sign_file(context, 'from', 'blah', to=to) == expected
#
#
## sign_file {{{1
# @pytest.mark.asyncio
# @pytest.mark.parametrize('to,expected', (
#    (None, 'from'),
#    ('to', 'to')))
# async def test_sign_file_autograph(context, mocker, to, expected):
#    context.task = {
#        'scopes': ['project:releng:signing:cert:dep-signing']
#    }
#    context.signing_servers = {
#        "project:releng:signing:cert:dep-signing": [
#            SigningServer(*["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_mar"], "autograph"])
#        ]
#    }
#    mocker.patch.object(sign, 'sign_file_with_autograph', new=noop_async)
#
#    assert await sign.sign_file(context, 'from', 'autograph_mar', to=to) == expected
#
#
# @pytest.mark.asyncio
# @pytest.mark.parametrize('to,expected,format,options', (
#    (None, 'from', 'autograph_mar', None),
#    ('to', 'to', 'autograph_mar', None),
#    ('to', 'to', 'autograph_apk_foo', {'zip': 'passthrough'}),
#    ('to', 'to', 'autograph_apk_sha1', {'pkcs7_digest': 'SHA1', 'zip': 'passthrough'})))
# async def test_sign_file_with_autograph(context, mocker, to, expected, format, options):
#    open_mock = mocker.mock_open(read_data=b'0xdeadbeef')
#    mocker.patch('builtins.open', open_mock, create=True)
#
#    session_mock = mocker.MagicMock()
#    session_mock.post.return_value.json.return_value = [{'signed_file': 'bW96aWxsYQ=='}]
#
#    Session_mock = mocker.Mock()
#    Session_mock.return_value.__enter__ = mocker.Mock(return_value=session_mock)
#    Session_mock.return_value.__exit__ = mocker.Mock()
#    mocker.patch('signingscript.sign.requests.Session', Session_mock, create=True)
#
#    context.task = {
#        'scopes': ['project:releng:signing:cert:dep-signing']
#    }
#    context.signing_servers = {
#        "project:releng:signing:cert:dep-signing": [
#            SigningServer(*["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", [format], "autograph"])
#        ]
#    }
#    assert await sign.sign_file_with_autograph(context, 'from', format, to=to) == expected
#    open_mock.assert_called()
#    kwargs = {'input': 'MHhkZWFkYmVlZg=='}
#    if options:
#        kwargs['options'] = options
#    session_mock.post.assert_called_with(
#        'https://autograph-hsm.dev.mozaws.net/sign/file',
#        auth=mocker.ANY,
#        json=[kwargs])
#
#
# @pytest.mark.asyncio
# @pytest.mark.parametrize('to,expected', (
#    (None, 'from',),
#    ('to', 'to')))
# async def test_sign_file_with_autograph_invalid_format_errors(context, mocker, to, expected):
#    context.task = {
#        'scopes': ['project:releng:signing:cert:dep-signing']
#    }
#    context.signing_servers = {}
#    with pytest.raises(IScriptError):
#        await sign.sign_file_with_autograph(context, 'from', 'mar', to=to)
#
#
# @pytest.mark.asyncio
# @pytest.mark.parametrize('to,expected', (
#    (None, 'from',),
#    ('to', 'to')))
# async def test_sign_file_with_autograph_no_suitable_servers_errors(context, mocker, to, expected):
#    context.task = {
#        'scopes': ['project:releng:signing:cert:dep-signing']
#    }
#    context.signing_servers = {}
#    with pytest.raises(IScriptError):
#        await sign.sign_file_with_autograph(context, 'from', 'autograph_mar', to=to)
#
#
# @pytest.mark.asyncio
# @pytest.mark.parametrize('to,expected', ((
#    None, 'from',
# ), (
#    'to', 'to'
# )))
# async def test_sign_file_with_autograph_raises_http_error(context, mocker, to, expected):
#    open_mock = mocker.mock_open(read_data=b'0xdeadbeef')
#    mocker.patch('builtins.open', open_mock, create=True)
#
#    session_mock = mocker.MagicMock()
#    post_mock_response = session_mock.post.return_value
#    post_mock_response.raise_for_status.side_effect = sign.requests.exceptions.RequestException
#    post_mock_response.json.return_value = [{'signed_file': 'bW96aWxsYQ=='}]
#
#    @contextmanager
#    def session_context():
#        yield session_mock
#
#    mocker.patch('signingscript.sign.requests.Session', session_context)
#
#    async def fake_retry_async(func, args=(), attempts=5, sleeptime_kwargs=None):
#        await func(*args)
#
#    mocker.patch.object(sign, 'retry_async', new=fake_retry_async)
#
#    context.task = {
#        'scopes': ['project:releng:signing:cert:dep-signing']
#    }
#    context.signing_servers = {
#        "project:releng:signing:cert:dep-signing": [
#            SigningServer(*["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_mar"], "autograph"])
#        ]
#    }
#    with pytest.raises(sign.requests.exceptions.RequestException):
#        await sign.sign_file_with_autograph(context, 'from', 'autograph_mar', to=to)
#    open_mock.assert_called()
#
#
## sign_macapp {{{1
# @pytest.mark.asyncio
# @pytest.mark.parametrize('filename,expected', ((
#    'foo.dmg', 'foo.tar.gz',
# ), (
#    'foo.tar.bz2', 'foo.tar.bz2',
# )))
# async def test_sign_macapp(context, mocker, filename, expected):
#    mocker.patch.object(sign, '_convert_dmg_to_tar_gz', new=noop_async)
#    mocker.patch.object(sign, 'sign_file', new=noop_async)
#    assert await sign.sign_macapp(context, filename, 'blah') == expected
#
#
## sign_signcode {{{1
# @pytest.mark.asyncio
# @pytest.mark.parametrize('filename,fmt,raises', ((
#    'foo.msi', 'sha2signcode', False
# ), (
#    'setup.exe', 'osslsigncode', False
# ), (
#    'foo.zip', 'signcode', False
# ), (
#    'raises.invalid.extension', 'sha2signcode', True
# )))
# async def test_sign_signcode(context, mocker, filename, fmt, raises):
#    files = ["x/foo.dll", "y/msvcblah.dll", "z/setup.exe", "ignore"]
#
#    async def fake_unzip(_, f, **kwargs):
#        assert f.endswith('.zip')
#        return files
#
#    async def fake_sign(_, filename, *args):
#        assert os.path.basename(filename) in ("foo.dll", "setup.exe", "foo.msi")
#
#    mocker.patch.object(sign, '_extract_zipfile', new=fake_unzip)
#    mocker.patch.object(sign, 'sign_file', new=fake_sign)
#    mocker.patch.object(sign, '_create_zipfile', new=noop_async)
#    if raises:
#        with pytest.raises(IScriptError):
#            await sign.sign_signcode(context, filename, fmt)
#    else:
#        await sign.sign_signcode(context, filename, fmt)
#
#
## sign_widevine {{{1
# @pytest.mark.asyncio
# @pytest.mark.parametrize('filename,fmt,raises,should_sign,orig_files', (
#    ('foo.tar.gz', 'widevine', False, True, None),
#    ('foo.zip', 'widevine_blessed', False, True, None),
#    ('foo.dmg', 'widevine', False, True, [
#        "foo.app/Contents/MacOS/firefox",
#        "foo.app/Contents/MacOS/bar.app/Contents/MacOS/plugin-container",
#        "foo.app/ignore",
#    ]),
#    ('foo.unknown', 'widevine', True, False, None),
#    ('foo.zip', 'widevine', False, False, None),
#    ('foo.dmg', 'widevine', False, False, None),
#    ('foo.tar.bz2', 'widevine', False, False, None),
#    ('foo.zip', 'autograph_widevine', False, True, None),
#    ('foo.dmg', 'autograph_widevine', False, True, None),
#    ('foo.tar.bz2', 'autograph_widevine', False, True, None),
# ))
# async def test_sign_widevine(context, mocker, filename, fmt, raises,
#                             should_sign, orig_files):
#    if should_sign:
#        files = orig_files or ["isdir/firefox", "firefox/firefox", "y/plugin-container", "z/blah", "ignore"]
#    else:
#        files = orig_files or ["z/blah", "ignore"]
#
#    async def fake_filelist(*args, **kwargs):
#        return files
#
#    async def fake_unzip(_, f, **kwargs):
#        assert f.endswith('.zip')
#        return files
#
#    async def fake_untar(_, f, comp, **kwargs):
#        assert f.endswith('.tar.{}'.format(comp.lstrip('.')))
#        return files
#
#    async def fake_undmg(_, f):
#        assert f.endswith('.dmg')
#
#    async def fake_sign(_, f, fmt, **kwargs):
#        if f.endswith("firefox"):
#            assert fmt == "widevine"
#        elif f.endswith("container"):
#            assert fmt == "widevine_blessed"
#        else:
#            assert False, "unexpected file and format {} {}!".format(f, fmt)
#        if 'MacOS' in f:
#            assert f not in files, "We should have renamed this file!"
#
#    def fake_isfile(path):
#        return 'isdir' not in path
#
#    mocker.patch.object(sign, '_get_tarfile_files', new=fake_filelist)
#    mocker.patch.object(sign, '_extract_tarfile', new=fake_untar)
#    mocker.patch.object(sign, '_get_zipfile_files', new=fake_filelist)
#    mocker.patch.object(sign, '_extract_zipfile', new=fake_unzip)
#    mocker.patch.object(sign, '_convert_dmg_to_tar_gz', new=fake_undmg)
#    mocker.patch.object(sign, 'sign_file', new=noop_async)
#    mocker.patch.object(sign, 'sign_widevine_with_autograph', new=noop_async)
#    mocker.patch.object(sign, 'makedirs', new=noop_sync)
#    mocker.patch.object(sign, 'generate_precomplete', new=noop_sync)
#    mocker.patch.object(sign, '_create_tarfile', new=noop_async)
#    mocker.patch.object(sign, '_create_zipfile', new=noop_async)
#    mocker.patch.object(sign, '_run_generate_precomplete', new=noop_sync)
#    mocker.patch.object(os.path, 'isfile', new=fake_isfile)
#
#    if raises:
#        with pytest.raises(IScriptError):
#            await sign.sign_widevine(context, filename, fmt)
#    else:
#        await sign.sign_widevine(context, filename, fmt)
#
#
## _get_widevine_signing_files {{{1
# @pytest.mark.parametrize('filenames,expected', ((
#    ['firefox.dll', 'XUL.so', 'firefox.bin', 'blah'], {}
# ), (
#    ('firefox', 'blah/XUL', 'foo/bar/libclearkey.dylib', 'baz/plugin-container', 'ignore'), {
#        'firefox': 'widevine',
#        'blah/XUL': 'widevine',
#        'foo/bar/libclearkey.dylib': 'widevine',
#        'baz/plugin-container': 'widevine_blessed',
#    }
# ), (
#    # Test for existing signature files
#    (
#        'firefox', 'blah/XUL', 'blah/XUL.sig',
#        'foo/bar/libclearkey.dylib', 'foo/bar/libclearkey.dylib.sig',
#        'plugin-container', 'plugin-container.sig', 'ignore'
#    ),
#    {'firefox': 'widevine'}
# )))
# def test_get_widevine_signing_files(filenames, expected):
#    assert sign._get_widevine_signing_files(filenames) == expected
#
#
## _run_generate_precomplete {{{1
# @pytest.mark.parametrize("num_precomplete,raises", ((
#    1, False,
# ), (
#    0, True,
# ), (
#    2, True,
# )))
# def test_run_generate_precomplete(context, num_precomplete, raises, mocker):
#    mocker.patch.object(sign, "generate_precomplete", new=noop_sync)
#    work_dir = context.config['work_dir']
#    for i in range(0, num_precomplete):
#        path = os.path.join(work_dir, "foo", str(i))
#        makedirs(path)
#        with open(os.path.join(path, "precomplete"), "w") as fh:
#            fh.write("blah")
#    if raises:
#        with pytest.raises(IScriptError):
#            sign._run_generate_precomplete(context, work_dir)
#    else:
#        sign._run_generate_precomplete(context, work_dir)
#
#
## remove_extra_files {{{1
# def test_remove_extra_files(context):
#    extra = ["a", "b/c"]
#    good = ["d", "e/f"]
#    work_dir = context.config['work_dir']
#    all_files = []
#    for f in extra + good:
#        path = os.path.join(work_dir, f)
#        makedirs(os.path.dirname(path))
#        with open(path, "w") as fh:
#            fh.write("x")
#        if f in good:
#            all_files.append(path)
#    for f in good:
#        assert os.path.exists(os.path.join(work_dir, f))
#    output = sign.remove_extra_files(work_dir, all_files)
#    for f in extra:
#        path = os.path.realpath(os.path.join(work_dir, f))
#        assert path in output
#        assert not os.path.exists(path)
#    for f in good:
#        assert os.path.exists(os.path.join(work_dir, f))
#
#
# autograph {{{1
@pytest.mark.asyncio
async def test_bad_autograph_method():
    with pytest.raises(IScriptError):
        await iwv.sign_with_autograph(None, None, None, "badformat")


@pytest.mark.asyncio
@pytest.mark.parametrize("blessed", (True, False))
async def test_widevine_autograph(mocker, tmp_path, blessed):
    wv = mocker.patch("iscript.widevine.widevine")
    wv.generate_widevine_hash.return_value = b"hashhashash"
    wv.generate_widevine_signature.return_value = b"sigwidevinesig"
    called_format = None

    async def fake_sign(key_config, h, fmt, *args):
        nonlocal called_format
        called_format = fmt
        return base64.b64encode(b"sigautographsig")

    mocker.patch.object(iwv, "sign_with_autograph", fake_sign)

    cert = tmp_path / "widevine.crt"
    cert.write_bytes(b"TMPCERT")
    key_config = {"widevine_cert": cert}

    to = tmp_path / "signed.sig"
    to = await iwv.sign_widevine_with_autograph(key_config, "from", blessed, to=to)

    assert b"sigwidevinesig" == to.read_bytes()
    assert called_format == "autograph_widevine"


@pytest.mark.asyncio
async def test_no_widevine(mocker, tmp_path):
    async def fake_sign_hash(*args, **kwargs):
        return b"sigautographsig"

    mocker.patch.object(iwv, "sign_hash_with_autograph", fake_sign_hash)

    with pytest.raises(ImportError):
        to = tmp_path / "signed.sig"
        to = await iwv.sign_widevine_with_autograph({}, "from", True, to=to)
