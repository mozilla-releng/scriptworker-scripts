import json
import pytest
import tempfile

from scriptworker.context import Context
from beetmoverscript.test import (get_fake_valid_task, get_fake_valid_config,
                                  get_fake_balrog_props, get_fake_checksums_manifest)
from beetmoverscript.utils import (generate_beetmover_manifest, get_hash,
                                   write_json, generate_beetmover_template_args,
                                   write_file, is_action_a_release_shipping)
from beetmoverscript.constants import HASH_BLOCK_SIZE


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


def test_write_json():
    sample_data = get_fake_balrog_props()

    with tempfile.NamedTemporaryFile(delete=True) as fp:
        write_json(fp.name, sample_data)

        with open(fp.name, "r") as fread:
            retrieved_data = json.load(fread)

        assert sample_data == retrieved_data


def test_write_file():
    sample_data = "\n".join(get_fake_checksums_manifest())

    with tempfile.NamedTemporaryFile(delete=True) as fp:
        write_file(fp.name, sample_data)

        with open(fp.name, "r") as fread:
            retrieved_data = fread.read()

        assert sample_data == retrieved_data


def test_generate_manifest():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.release_props = get_fake_balrog_props()["properties"]
    context.release_props['platform'] = context.release_props['stage_platform']
    context.bucket = 'nightly'
    context.action = 'push-to-nightly'

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


@pytest.mark.parametrize("taskjson,partials", [
    ('task.json', {}),
    ('task_partials.json', {'target.partial-1.mar': '20170831150342'})
])
def test_beetmover_template_args_generation(taskjson, partials):
    context = Context()
    context.task = get_fake_valid_task(taskjson)
    context.config = get_fake_valid_config()
    context.release_props = get_fake_balrog_props()["properties"]
    context.release_props['platform'] = context.release_props['stage_platform']
    context.bucket = 'nightly'
    context.action = 'push-to-nightly'

    expected_template_args = {
        'branch': 'mozilla-central',
        'platform': 'android-api-15',
        'product': 'Fake',
        'stage_platform': 'android-api-15',
        'template_key': 'fennec_nightly',
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


@pytest.mark.parametrize("non_release", [
    'push-to-nightly',
    'push-to-releases',
    'push-to-staging',
])
@pytest.mark.parametrize("release", [
    'push-to-candidates',
])
def test_if_action_is_a_release_shipping(non_release, release):
    assert is_action_a_release_shipping(non_release) is False
    assert is_action_a_release_shipping(release) is True
