import tempfile
import json

from scriptworker.context import Context
from beetmoverscript.test import (get_fake_valid_task, get_fake_valid_config,
                                  get_fake_balrog_props, get_fake_checksums_manifest)
from beetmoverscript.utils import (generate_beetmover_manifest, get_hash,
                                   write_json, generate_beetmover_template_args,
                                   get_checksums_base_filename, write_file)
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
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']
    template_args = generate_beetmover_template_args(context.task,
                                                     context.properties)
    manifest = generate_beetmover_manifest(context.config, template_args)
    mapping = manifest['mapping']
    s3_keys = [mapping[m].get('target_info.txt', {}).get('s3_key') for m in mapping]
    assert sorted(mapping.keys()) == ['en-US', 'multi']
    assert sorted(s3_keys) == ['en-US/fake-99.0a1.en-US.target_info.txt',
                               'fake-99.0a1.multi.target_info.txt']
    assert (
        manifest.get('s3_prefix_dated') ==
        'pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/' and
        manifest.get('s3_prefix_latest') == 'pub/mobile/nightly/latest-mozilla-central-fake/'
    )


def test_checksums_filename_generation():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']
    template_args = generate_beetmover_template_args(context.task,
                                                     context.properties)
    pretty_name = get_checksums_base_filename(template_args)
    assert pretty_name == 'fake-99.0a1.en-US.android-api-15.checksums'


def test_beetmover_template_args_generation():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.properties = get_fake_balrog_props()["properties"]
    context.properties['platform'] = context.properties['stage_platform']

    expected_template_args = {
        'branch': 'mozilla-central',
        'platform': 'android-api-15',
        'product': 'Fake',
        'stage_platform': 'android-api-15',
        'template_key': 'fennec_nightly',
        'upload_date': '2016/09/2016-09-01-16-26-14',
        'version': '99.0a1'
    }

    template_args = generate_beetmover_template_args(context.task,
                                                     context.properties)
    assert template_args == expected_template_args

    context.task['payload']['locale'] = 'ro'
    template_args = generate_beetmover_template_args(context.task,
                                                     context.properties)

    assert template_args['template_key'] == 'fake_nightly_repacks'
