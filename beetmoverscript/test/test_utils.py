import json
import pytest
import tempfile

from beetmoverscript.test import (context, get_fake_valid_task,
                                  get_fake_balrog_props, get_fake_checksums_manifest,
                                  get_test_jinja_env)
import beetmoverscript.utils as butils
from beetmoverscript.utils import (generate_beetmover_manifest, get_hash,
                                   write_json, generate_beetmover_template_args,
                                   write_file, is_release_action, is_promotion_action,
                                   get_partials_props, matches_exclude, get_candidates_prefix,
                                   get_releases_prefix, get_product_name)
from beetmoverscript.constants import HASH_BLOCK_SIZE

assert context  # silence pyflakes


# get_hash {{{1
def test_get_hash():
    correct_sha1 = 'cb8aa4802996ac8de0436160e7bc0c79b600c222'
    text = b'Hello world from beetmoverscript!'

    with tempfile.NamedTemporaryFile(delete=True) as fp:
        # we generate a file by repeatedly appending the `text` to make sure we
        # overcome the HASH_BLOCK_SIZE chunk digest update line
        count = int(HASH_BLOCK_SIZE / len(text)) * 2
        for i in range(count):
            fp.write(text)
        sha1digest = get_hash(fp.name, hash_type="sha1")

    assert correct_sha1 == sha1digest


# write_json {{{1
def test_write_json():
    sample_data = get_fake_balrog_props()

    with tempfile.NamedTemporaryFile(delete=True) as fp:
        write_json(fp.name, sample_data)

        with open(fp.name, "r") as fread:
            retrieved_data = json.load(fread)

        assert sample_data == retrieved_data


# write_file {{{1
def test_write_file():
    sample_data = "\n".join(get_fake_checksums_manifest())

    with tempfile.NamedTemporaryFile(delete=True) as fp:
        write_file(fp.name, sample_data)

        with open(fp.name, "r") as fread:
            retrieved_data = fread.read()

        assert sample_data == retrieved_data


# generate_beetmover_manifest {{{1
def test_generate_manifest(context, mocker):
    mocker.patch('beetmoverscript.utils.get_jinja_env', get_test_jinja_env)
    manifest = generate_beetmover_manifest(context)
    mapping = manifest['mapping']
    s3_keys = [mapping[m].get('target_info.txt', {}).get('s3_key') for m in mapping]
    assert sorted(mapping.keys()) == ['en-US', 'multi']
    assert sorted(s3_keys) == ['fake-99.0a1.en-US.target_info.txt',
                               'fake-99.0a1.multi.target_info.txt']

    expected_destinations = {
        'en-US': ['2016/09/2016-09-01-16-26-14-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_info.txt',
                  'latest-mozilla-central-fake/en-US/fake-99.0a1.en-US.target_info.txt'],
        'multi': ['2016/09/2016-09-01-16-26-14-mozilla-central-fake/fake-99.0a1.multi.target_info.txt',
                  'latest-mozilla-central-fake/fake-99.0a1.multi.target_info.txt']
    }

    actual_destinations = {
        k: mapping[k]['target_info.txt']['destinations'] for k in sorted(mapping.keys())
    }

    assert expected_destinations == actual_destinations


# generate_beetmover_template_args {{{1
@pytest.mark.parametrize("taskjson,partials", [
    ('task.json', {}),
    ('task_partials.json', {'target.partial-1.mar': {
        'artifact_name': 'target.partial-1.mar',
        'buildid': '20170831150342',
        'locale': 'be',
        'platform': 'win32',
        'previousBuildNumber': '1',
        'previousVersion': '56.0.2'
    }})
])
def test_beetmover_template_args_generation(context, taskjson, partials):
    context.task = get_fake_valid_task(taskjson)
    expected_template_args = {
        'branch': 'mozilla-central',
        'platform': 'android-api-15',
        'filename_platform': 'android-arm',
        'product': 'Fake',
        'stage_platform': 'android-api-15',
        'template_key': 'fake_nightly',
        'upload_date': '2016/09/2016-09-01-16-26-14',
        'version': '99.0a1',
        'buildid': '20990205110000',
        'partials': partials,
    }

    template_args = generate_beetmover_template_args(context)
    assert template_args == expected_template_args

    context.task['payload']['locale'] = 'ro'
    template_args = generate_beetmover_template_args(context)

    assert template_args['template_key'] == 'fake_nightly_repacks'


def test_beetmover_template_args_generation_release(context):
    context.bucket = 'dep'
    context.action = 'push-to-candidates'
    context.task['payload']['build_number'] = 3
    context.task['payload']['version'] = '4.4'

    expected_template_args = {
        'branch': 'mozilla-central',
        'platform': 'android-api-15',
        'filename_platform': 'android-arm',
        'product': 'Fake',
        'stage_platform': 'android-api-15',
        'template_key': 'fake_candidates',
        'upload_date': '2016/09/2016-09-01-16-26-14',
        'version': '4.4',
        'buildid': '20990205110000',
        'partials': {},
        'build_number': 3,
    }

    template_args = generate_beetmover_template_args(context)
    assert template_args == expected_template_args


# is_release_action is_promotion_action {{{1
@pytest.mark.parametrize("action,release,promotion", ((
    'push-to-nightly', False, False,
), (
    'push-to-candidates', False, True,
), (
    'push-to-releases', True, False,
)))
def test_is_action_release_or_promotion(action, release, promotion):
    assert is_release_action(action) is release
    assert is_promotion_action(action) is promotion


# get_partials_props {{{1
@pytest.mark.parametrize("taskjson,expected", [
    ('task.json', {}),
    ('task_partials.json', {'target.partial-1.mar': {
        'artifact_name': 'target.partial-1.mar',
        'buildid': '20170831150342',
        'locale': 'be',
        'platform': 'win32',
        'previousBuildNumber': '1',
        'previousVersion': '56.0.2'
    }})
])
def test_get_partials_props(taskjson, expected):
    partials_props = get_partials_props(get_fake_valid_task(taskjson))
    assert partials_props == expected


# alter_unpretty_contents {{{1
def test_alter_unpretty_contents(context, mocker):
    context.artifacts_to_beetmove = {
        'loc1': {'target.test_packages.json': 'mobile'},
        'loc2': {'target.test_packages.json': 'mobile'},
    }

    mappings = {
        'mapping': {
            'loc1': {
                'bar': {
                    's3_key': 'x'
                },
            },
            'loc2': {},
        },
    }

    def fake_json(*args, **kwargs):
        return {'mobile': ['bar']}

    mocker.patch.object(butils, 'load_json', new=fake_json)
    mocker.patch.object(butils, 'write_json', new=fake_json)
    butils.alter_unpretty_contents(context, ['target.test_packages.json'], mappings)


# get_candidates_prefix {{{1
@pytest.mark.parametrize("product,version,build_number,expected", ((
    "fennec", "bar", "baz", "pub/mobile/candidates/bar-candidates/buildbaz/"
), (
    "mobile", "99.0a3", 14, "pub/mobile/candidates/99.0a3-candidates/build14/"
)))
def test_get_candidates_prefix(product, version, build_number, expected):
    assert get_candidates_prefix(product, version, build_number) == expected


# get_releases_prefix {{{1
@pytest.mark.parametrize("product,version,expected", ((
    "firefox", "bar", "pub/firefox/releases/bar/"
), (
    "fennec", "99.0a3", "pub/mobile/releases/99.0a3/"
)))
def test_get_releases_prefix(product, version, expected):
    assert get_releases_prefix(product, version) == expected


# matches_exclude {{{1
@pytest.mark.parametrize("keyname,expected", ((
    "blah.excludeme", True
), (
    "foo/metoo/blah", True
), (
    "mobile.zip", False
)))
def test_matches_exclude(keyname, expected):
    excludes = [
        r"^.*.excludeme$",
        r"^.*/metoo/.*$",
    ]
    assert matches_exclude(keyname, excludes) == expected


# product_name {{{1
@pytest.mark.parametrize("appName,tmpl_key,expected", ((
    "firefox", "dummy", "firefox",
), (
    "firefox", "devedition", "devedition",
), (
    "Firefox", "devedition", "Devedition",
), (
    "Fennec", "dummy", "Fennec",
), (
    "Firefox", "dummy", "Firefox",
), (
    "fennec", "dummy", "fennec",
)))
def test_get_product_name(appName, tmpl_key, expected):
    assert get_product_name(appName, tmpl_key) == expected
