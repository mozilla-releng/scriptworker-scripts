from beetmoverscript.test import get_fake_valid_task, get_fake_valid_config
from beetmoverscript.utils import generate_candidates_manifest
from scriptworker.context import Context


def test_generate_manifest():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    manifest = generate_candidates_manifest(context)
    mapping = manifest['mapping']
    artifacts = [mapping[m].get('package', {}).get('artifact') for m in mapping]
    s3_keys = [mapping[m].get('package', {}).get('s3_key') for m in mapping]
    assert sorted(mapping.keys()) == ['en-US', 'multi']
    assert sorted(artifacts) == ['en-US/target.package', 'target.package']
    assert sorted(s3_keys) == ['en-US/fake-99.0a1.en-US.fake.package',
                               'fake-99.0a1.multi.fake.package']
    assert (
        manifest.get('s3_prefix_dated') ==
        'pub/mobile/nightly/2016/09/2016-09-01-16-26-14-mozilla-central-fake/' and
        manifest.get('s3_prefix_latest') == 'pub/mobile/nightly/latest-mozilla-central-fake/'
    )
