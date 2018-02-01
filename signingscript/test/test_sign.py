from contextlib import contextmanager
import os
import os.path
import pytest
import shutil
import tarfile
import zipfile

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.utils import makedirs

from signingscript.exceptions import SigningScriptError
from signingscript.script import get_default_config
from signingscript.utils import get_hash, load_signing_server_config, mkdir, SigningServer
import signingscript.sign as sign
import signingscript.utils as utils
from signingscript.test import noop_sync, noop_async, tmpdir, die, BASE_DIR, TEST_DATA_DIR

assert tmpdir  # silence flake8


# helper constants, fixtures, functions {{{1
SERVER_CONFIG_PATH = os.path.join(BASE_DIR, 'example_server_config.json')
DEFAULT_SCOPE_PREFIX = 'project:releng:signing:'
TEST_CERT_TYPE = '{}cert:dep-signing'.format(DEFAULT_SCOPE_PREFIX)


@pytest.fixture(scope='function')
def task_defn():
    return {
        'provisionerId': 'meh',
        'workerType': 'workertype',
        'schedulerId': 'task-graph-scheduler',
        'taskGroupId': 'some',
        'routes': [],
        'retries': 5,
        'created': '2015-05-08T16:15:58.903Z',
        'deadline': '2015-05-08T18:15:59.010Z',
        'expires': '2016-05-08T18:15:59.010Z',
        'dependencies': ['VALID_TASK_ID'],
        'scopes': ['signing'],
        'payload': {
          'upstreamArtifacts': [{
            'taskType': 'build',
            'taskId': 'VALID_TASK_ID',
            'formats': ['gpg'],
            'paths': ['public/build/firefox-52.0a1.en-US.win64.installer.exe'],
          }]
        }
    }


@pytest.yield_fixture(scope='function')
def context(tmpdir):
    context = Context()
    context.config = get_default_config()
    context.config['signing_server_config'] = SERVER_CONFIG_PATH
    context.config['work_dir'] = os.path.join(tmpdir, 'work')
    context.config['artifact_dir'] = os.path.join(tmpdir, 'artifact')
    context.config['taskcluster_scope_prefix'] = DEFAULT_SCOPE_PREFIX
    context.signing_servers = load_signing_server_config(context)
    mkdir(context.config['work_dir'])
    mkdir(context.config['artifact_dir'])
    yield context


@contextmanager
def context_die(*args, **kwargs):
    raise SigningScriptError("dying")


async def helper_archive(context, filename, create_fn, extract_fn, *kwargs):
    tmpdir = context.config['artifact_dir']
    archive = os.path.join(context.config['work_dir'], filename)
    # Add a directory to tickle the tarfile isfile() call
    files = [__file__, SERVER_CONFIG_PATH]
    await create_fn(
        context, archive, [__file__, SERVER_CONFIG_PATH], *kwargs,
        tmp_dir=BASE_DIR
    )
    await extract_fn(context, archive, *kwargs, tmp_dir=tmpdir)
    for path in files:
        target_path = os.path.join(tmpdir, os.path.relpath(path, BASE_DIR))
        assert os.path.exists(target_path)
        assert os.path.isfile(target_path)
        hash1 = get_hash(path)
        hash2 = get_hash(target_path)
        assert hash1 == hash2


# get_suitable_signing_servers {{{1
@pytest.mark.parametrize('formats,expected', ((
    ['gpg'], [["127.0.0.1:9110", "user", "pass", ["gpg", "sha2signcode"]]]
), (
    ['invalid'], []
)))
def test_get_suitable_signing_servers(context, formats, expected):
    expected_servers = []
    for info in expected:
        expected_servers.append(
            SigningServer(*info)
        )

    assert sign.get_suitable_signing_servers(
        context.signing_servers, TEST_CERT_TYPE,
        formats
    ) == expected_servers


# build_signtool_cmd {{{1
@pytest.mark.parametrize('signtool,from_,to,fmt', ((
    "signtool", "blah", "blah", "gpg"
), (
    ["signtool"], "blah", "blah", "sha2signcode"
)))
def test_build_signtool_cmd(context, signtool, from_, to, fmt):
    context.config['signtool'] = signtool
    context.task = {
        "scopes": [
            "project:releng:signing:cert:dep-signing",
            "project:releng:signing:format:gpg",
            "project:releng:signing:format:sha2signcode",
        ],
    }
    context.config['ssl_cert'] = 'cert'
    work_dir = context.config['work_dir']
    assert sign.build_signtool_cmd(context, from_, fmt, to=to) == [
        'signtool', "-v",
        "-n", os.path.join(work_dir, "nonce"),
        "-t", os.path.join(work_dir, "token"),
        "-c", 'cert',
        "-H", "127.0.0.1:9110",
        "-f", fmt,
        "-o", to, from_,
    ]


# sign_file {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('to,expected', ((
    None, 'from',
), (
    'to', 'to'
)))
async def test_sign_file(context, mocker, to, expected):
    mocker.patch.object(sign, 'build_signtool_cmd', new=noop_sync)
    mocker.patch.object(utils, 'execute_subprocess', new=noop_async)
    assert await sign.sign_file(context, 'from', 'blah', to=to) == expected


# sign_gpg {{{1
@pytest.mark.asyncio
async def test_sign_gpg(context, mocker):
    mocker.patch.object(sign, 'sign_file', new=noop_async)
    assert await sign.sign_gpg(context, 'from', 'blah') == ['from', 'from.asc']


# sign_jar {{{1
@pytest.mark.asyncio
async def test_sign_jar(context, mocker):
    counter = []

    async def fake_zipalign(*args):
        counter.append('1')

    mocker.patch.object(sign, 'sign_file', new=noop_async)
    mocker.patch.object(sign, 'zip_align_apk', new=fake_zipalign)
    await sign.sign_jar(context, 'from', 'blah')
    assert len(counter) == 1


# sign_macapp {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('filename,expected', ((
    'foo.dmg', 'foo.tar.gz',
), (
    'foo.tar.bz2', 'foo.tar.bz2',
)))
async def test_sign_macapp(context, mocker, filename, expected):
    mocker.patch.object(sign, '_convert_dmg_to_tar_gz', new=noop_async)
    mocker.patch.object(sign, 'sign_file', new=noop_async)
    assert await sign.sign_macapp(context, filename, 'blah') == expected


# sign_signcode {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('filename,fmt', ((
    'foo.tar.gz', 'sha2signcode'
), (
    'setup.exe', 'osslsigncode'
), (
    'foo.zip', 'signcode'
)))
async def test_sign_signcode(context, mocker, filename, fmt):
    files = ["x/foo.dll", "y/msvcblah.dll", "z/setup.exe", "ignore"]

    async def fake_unzip(_, f, **kwargs):
        assert f.endswith('.zip')
        return files

    async def fake_sign(_, filename, *args):
        assert os.path.basename(filename) in ("foo.dll", "setup.exe")

    mocker.patch.object(sign, '_extract_zipfile', new=fake_unzip)
    mocker.patch.object(sign, 'sign_file', new=fake_sign)
    mocker.patch.object(sign, '_create_zipfile', new=noop_async)
    await sign.sign_signcode(context, filename, fmt)


# sign_widevine {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('filename,fmt,raises,should_sign,orig_files', ((
    'foo.tar.gz', 'widevine', False, True, None
), (
    'foo.zip', 'widevine_blessed', False, True, None
), (
    'foo.dmg', 'widevine', False, True, [
        "foo.app/Contents/MacOS/firefox",
        "foo.app/Contents/MacOS/bar.app/Contents/MacOS/plugin-container",
        "foo.app/ignore",
    ]
), (
    'foo.unknown', 'widevine', True, False, None
), (
    'foo.zip', 'widevine', False, False, None
), (
    'foo.dmg', 'widevine', False, False, None
), (
    'foo.tar.bz2', 'widevine', False, False, None
)))
async def test_sign_widevine(context, mocker, filename, fmt, raises,
                             should_sign, orig_files):
    if should_sign:
        files = orig_files or ["isdir/firefox", "firefox/firefox", "y/plugin-container", "z/blah", "ignore"]
    else:
        files = orig_files or ["z/blah", "ignore"]

    async def fake_filelist(*args, **kwargs):
        return files

    async def fake_unzip(_, f, **kwargs):
        assert f.endswith('.zip')
        return files

    async def fake_untar(_, f, comp, **kwargs):
        assert f.endswith('.tar.{}'.format(comp.lstrip('.')))
        return files

    async def fake_undmg(_, f):
        assert f.endswith('.dmg')

    async def fake_sign(_, f, fmt, **kwargs):
        if f.endswith("firefox"):
            assert fmt == "widevine"
        elif f.endswith("container"):
            assert fmt == "widevine_blessed"
        else:
            assert False, "unexpected file and format {} {}!".format(f, fmt)
        if 'MacOS' in f:
            assert f not in files, "We should have renamed this file!"

    def fake_isfile(path):
        return 'isdir' not in path


    mocker.patch.object(sign, '_get_tarfile_files', new=fake_filelist)
    mocker.patch.object(sign, '_extract_tarfile', new=fake_untar)
    mocker.patch.object(sign, '_get_zipfile_files', new=fake_filelist)
    mocker.patch.object(sign, '_extract_zipfile', new=fake_unzip)
    mocker.patch.object(sign, '_convert_dmg_to_tar_gz', new=fake_undmg)
    mocker.patch.object(sign, 'sign_file', new=noop_async)
    mocker.patch.object(sign, 'makedirs', new=noop_sync)
    mocker.patch.object(sign, 'generate_precomplete', new=noop_sync)
    mocker.patch.object(sign, '_create_tarfile', new=noop_async)
    mocker.patch.object(sign, '_create_zipfile', new=noop_async)
    mocker.patch.object(sign, '_run_generate_precomplete', new=noop_sync)
    mocker.patch.object(os.path, 'isfile', new=fake_isfile)
    if raises:
        with pytest.raises(SigningScriptError):
            await sign.sign_widevine(context, filename, fmt)
    else:
        await sign.sign_widevine(context, filename, fmt)


# _should_sign_windows {{{1
@pytest.mark.parametrize('filenames,expected', ((
    ('firefox', 'libclearkey.dylib', 'D3DCompiler_42.dll', 'msvcblah.dll'), False
), (
    ('firefox.dll', 'foo.exe'), True
)))
def test_should_sign_windows(filenames, expected):
    for f in filenames:
        assert sign._should_sign_windows(f) == expected


# _get_widevine_signing_files {{{1
@pytest.mark.parametrize('filenames,expected', ((
    ['firefox.dll', 'XUL.so', 'firefox.bin', 'blah'], {}
), (
    ('firefox', 'blah/XUL', 'foo/bar/libclearkey.dylib', 'baz/plugin-container', 'ignore'), {
        'firefox': 'widevine',
        'blah/XUL': 'widevine',
        'foo/bar/libclearkey.dylib': 'widevine',
        'baz/plugin-container': 'widevine_blessed',
    }
), (
    # Test for existing signature files
    (
        'firefox', 'blah/XUL', 'blah/XUL.sig',
        'foo/bar/libclearkey.dylib', 'foo/bar/libclearkey.dylib.sig',
        'plugin-container', 'plugin-container.sig', 'ignore'
    ),
    {'firefox': 'widevine'}
)))
def test_get_widevine_signing_files(filenames, expected):
    assert sign._get_widevine_signing_files(filenames) == expected


# _run_generate_precomplete {{{1
@pytest.mark.parametrize("num_precomplete,raises", ((
    1, False,
), (
    0, True,
), (
    2, True,
)))
def test_run_generate_precomplete(context, num_precomplete, raises, mocker):
    mocker.patch.object(sign, "generate_precomplete", new=noop_sync)
    work_dir = context.config['work_dir']
    for i in range(0, num_precomplete):
        path = os.path.join(work_dir, "foo", str(i))
        makedirs(path)
        with open(os.path.join(path, "precomplete"), "w") as fh:
            fh.write("blah")
    if raises:
        with pytest.raises(SigningScriptError):
            sign._run_generate_precomplete(context, work_dir)
    else:
        sign._run_generate_precomplete(context, work_dir)


# remove_extra_files {{{1
def test_remove_extra_files(context):
    extra = ["a", "b/c"]
    good = ["d", "e/f"]
    work_dir = context.config['work_dir']
    all_files = []
    for f in extra + good:
        path = os.path.join(work_dir, f)
        makedirs(os.path.dirname(path))
        with open(path, "w") as fh:
            fh.write("x")
        if f in good:
            all_files.append(path)
    for f in good:
        assert os.path.exists(os.path.join(work_dir, f))
    output = sign.remove_extra_files(work_dir, all_files)
    for f in extra:
        path = os.path.realpath(os.path.join(work_dir, f))
        assert path in output
        assert not os.path.exists(path)
    for f in good:
        assert os.path.exists(os.path.join(work_dir, f))


# zip_align_apk {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('is_verbose', (True, False))
async def test_zip_align_apk(context, monkeypatch, is_verbose):
    context.config['zipalign'] = '/path/to/android/sdk/zipalign'
    context.config['verbose'] = is_verbose
    abs_to = '/absolute/path/to/apk.apk'

    async def execute_subprocess_mock(command):
        if is_verbose:
            assert command[0:4] == ['/path/to/android/sdk/zipalign', '-v', '4', abs_to]
            assert len(command) == 5
        else:
            assert command[0:3] == ['/path/to/android/sdk/zipalign', '4', abs_to]
            assert len(command) == 4

    def shutil_mock(_, destination):
        assert destination == abs_to

    monkeypatch.setattr('signingscript.utils.execute_subprocess', execute_subprocess_mock)
    monkeypatch.setattr('shutil.move', shutil_mock)

    await sign.zip_align_apk(context, abs_to)


# _convert_dmg_to_tar_gz {{{1
@pytest.mark.asyncio
async def test_convert_dmg_to_tar_gz(context, monkeypatch, tmpdir):
    dmg_path = 'path/to/foo.dmg'
    abs_dmg_path = os.path.join(context.config['work_dir'], dmg_path)
    tarball_path = 'path/to/foo.tar.gz'
    abs_tarball_path = os.path.join(context.config['work_dir'], tarball_path)

    async def execute_subprocess_mock(command, **kwargs):
        assert command in (
            ['dmg', 'extract', abs_dmg_path, 'tmp.hfs'],
            ['hfsplus', 'tmp.hfs', 'extractall', '/', '{}/app'.format(tmpdir)],
            ['tar', 'czvf', abs_tarball_path, '.'],
        )

    @contextmanager
    def fake_tmpdir():
        yield tmpdir

    monkeypatch.setattr('signingscript.utils.execute_subprocess', execute_subprocess_mock)
    monkeypatch.setattr('tempfile.TemporaryDirectory', fake_tmpdir)

    await sign._convert_dmg_to_tar_gz(context, dmg_path)


# _extract_zipfile _create_zipfile {{{1
@pytest.mark.asyncio
async def test_get_zipfile_files():
    assert sorted(
        await sign._get_zipfile_files(os.path.join(TEST_DATA_DIR, "test.zip"))
    ) == ["a", "b", "c/", "c/d", "c/e/", "c/e/f"]


@pytest.mark.asyncio
async def test_working_zipfile(context):
    await helper_archive(
        context, "foo.zip", sign._create_zipfile, sign._extract_zipfile
    )
    files = ["c/d", "c/e/f"]
    tmp_dir = os.path.join(context.config['work_dir'], "foo")
    expected = [os.path.join(tmp_dir, f) for f in files]
    assert await sign._extract_zipfile(
        context, os.path.join(TEST_DATA_DIR, "test.zip"),
        files=files, tmp_dir=tmp_dir
    ) == expected
    for f in expected:
        assert os.path.exists(f)


@pytest.mark.asyncio
async def test_bad_create_zipfile(context, mocker):
    mocker.patch.object(zipfile, 'ZipFile', new=context_die)
    with pytest.raises(SigningScriptError):
        await sign._create_zipfile(context, "foo.zip", [])


@pytest.mark.asyncio
async def test_bad_extract_zipfile(context, mocker):
    mocker.patch.object(sign, 'rm', new=die)
    with pytest.raises(SigningScriptError):
        await sign._extract_zipfile(context, "foo.zip")


@pytest.mark.asyncio
async def test_zipfile_append_write(context):
    top_dir = os.path.dirname(os.path.dirname(__file__))
    rel_files = ["test/test_script.py", "test/test_sign.py"]
    abs_files = [os.path.join(top_dir, f) for f in rel_files]
    full_rel_files = ["a", "b", "c/", "c/d", "c/e/", "c/e/f"] + rel_files
    to = os.path.join(context.config['work_dir'], "test.zip")

    # mode='w' -- zipfile should only have these two files
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "test.zip"), to)
    await sign._create_zipfile(context, to, abs_files, tmp_dir=top_dir, mode='w')
    assert sorted(await sign._get_zipfile_files(to)) == rel_files

    # mode='a' -- zipfile should have previous files + new files
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "test.zip"), to)
    await sign._create_zipfile(context, to, abs_files, tmp_dir=top_dir, mode='a')
    assert sorted(await sign._get_zipfile_files(to)) == full_rel_files


# tarfile {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("path,compression", ((
    os.path.join(TEST_DATA_DIR, "test.tar.bz2"),
    "bz2"
), (
    os.path.join(TEST_DATA_DIR, "test.tar.gz"),
    "gz"
)))
async def test_get_tarfile_files(path, compression):
    assert sorted(
        await sign._get_tarfile_files(path, compression)
    ) == [".", "./a", "./b", "./c", "./c/d", "./c/e", "./c/e/f"]


@pytest.mark.parametrize("compression,expected,raises", ((
    ".gz", "gz", False
), (
    "bz2", "bz2", False
), (
    "superstrong_compression!!!", None, True
)))
def test_get_tarfile_compression(compression, expected, raises):
    if raises:
        with pytest.raises(SigningScriptError):
            sign._get_tarfile_compression(compression)
    else:
        assert sign._get_tarfile_compression(compression) == expected


@pytest.mark.asyncio
async def test_working_tarfile(context):
    await helper_archive(
        context, "foo.tar.gz", sign._create_tarfile, sign._extract_tarfile, "gz"
    )


@pytest.mark.asyncio
async def test_bad_create_tarfile(context, mocker):
    mocker.patch.object(tarfile, 'open', new=context_die)
    with pytest.raises(SigningScriptError):
        await sign._create_tarfile(context, "foo.tar.gz", [], ".bz2")


@pytest.mark.asyncio
async def test_bad_extract_tarfile(context, mocker):
    mocker.patch.object(tarfile, 'open', new=context_die)
    with pytest.raises(SigningScriptError):
        await sign._extract_tarfile(context, "foo.tar.gz", "gz")


@pytest.mark.asyncio
async def test_tarfile_append_write(context):
    top_dir = os.path.dirname(os.path.dirname(__file__))
    rel_files = ["test/test_script.py", "test/test_sign.py"]
    abs_files = [os.path.join(top_dir, f) for f in rel_files]
    full_rel_files = [".", "./a", "./b", "./c", "./c/d", "./c/e", "./c/e/f"] + rel_files
    to = os.path.join(context.config['work_dir'], "test.tar.bz2")

    # mode='w' -- tarfile should only have these two files
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "test.tar.bz2"), to)
    await sign._create_tarfile(
        context, to, abs_files, 'bz2', tmp_dir=top_dir
    )
    assert sorted(await sign._get_tarfile_files(to, 'bz2')) == rel_files
