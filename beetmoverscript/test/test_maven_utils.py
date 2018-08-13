import pytest

from beetmoverscript.maven_utils import get_maven_expected_files_per_archive_per_task_id


@pytest.mark.parametrize('upstream_artifacts_per_task_id, mapping_manifest, expected, raises', ((
    {
        'someTaskId': [{
            'paths': ['/work_dir/cot/someTaskId/public/build/target.maven.zip'],
        }],
    },
    {
        'mapping': {
            'en-US': {
                'geckoview-beta-x86-62.0b3.aar': {},
                'geckoview-beta-x86-62.0b3.aar.md5': {},
                'geckoview-beta-x86-62.0b3.aar.sha1': {},
                'geckoview-beta-x86-62.0b3.pom': {},
                'geckoview-beta-x86-62.0b3.pom.md5': {},
                'geckoview-beta-x86-62.0b3.pom.sha1': {},
                'geckoview-beta-x86-62.0b3-javadoc.jar': {},
                'geckoview-beta-x86-62.0b3-javadoc.jar.md5': {},
                'geckoview-beta-x86-62.0b3-javadoc.jar.sha1': {},
                'geckoview-beta-x86-62.0b3-sources.jar': {},
                'geckoview-beta-x86-62.0b3-sources.jar.md5': {},
                'geckoview-beta-x86-62.0b3-sources.jar.sha1': {},
            }
        },
        's3_bucket_path': 'maven2/org/mozilla/geckoview-beta-x86/62.0b3/',
    },
    {
        'someTaskId': {
            '/work_dir/cot/someTaskId/public/build/target.maven.zip': [
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3.aar',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3.aar.md5',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3.aar.sha1',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3.pom',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3.pom.md5',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3.pom.sha1',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3-javadoc.jar',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3-javadoc.jar.md5',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3-javadoc.jar.sha1',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3-sources.jar',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3-sources.jar.md5',
                'org/mozilla/geckoview-beta-x86/62.0b3/geckoview-beta-x86-62.0b3-sources.jar.sha1',
            ],
        },
    },
    False,
), (
    {
        'someTaskId': [{
            'paths': ['/work_dir/cot/someTaskId/public/build/target.jsshell.zip'],
        }],
    },
    {
        'mapping': {
            'en-US': {
                'geckoview-beta-x86-62.0b3.aar': {},
                'geckoview-beta-x86-62.0b3.aar.md5': {},
                'geckoview-beta-x86-62.0b3.aar.sha1': {},
                'geckoview-beta-x86-62.0b3-sources.jar.sha1': {},
            }
        },
        's3_bucket_path': 'maven2/org/mozilla/geckoview-beta-x86/62.0b3/',
    },
    {},
    True,
), (
    {
        'someTaskId': [{
            'paths': ['/work_dir/cot/someTaskId/public/build/target.maven.zip'],
        }],
        'someOtherTaskId': [{
            'paths': ['/work_dir/cot/someTaskId/public/build/target.maven.zip'],
        }],
    },
    {
        'mapping': {
            'en-US': {
                'geckoview-beta-x86-62.0b3.aar': {},
                'geckoview-beta-x86-62.0b3.aar.md5': {},
                'geckoview-beta-x86-62.0b3.aar.sha1': {},
                'geckoview-beta-x86-62.0b3-sources.jar.sha1': {},
            }
        },
        's3_bucket_path': 'maven2/org/mozilla/geckoview-beta-x86/62.0b3/',
    },
    {},
    True,
), (
    {
        'someTaskId': [{
            'paths': [
                '/work_dir/cot/someTaskId/public/build/target.maven.zip',
                '/work_dir/cot/someTaskId/public/build/other/folder/target.maven.zip'
            ],
        }],
    },
    {
        'mapping': {
            'en-US': {
                'geckoview-beta-x86-62.0b3.aar': {},
                'geckoview-beta-x86-62.0b3.aar.md5': {},
                'geckoview-beta-x86-62.0b3.aar.sha1': {},
                'geckoview-beta-x86-62.0b3-sources.jar.sha1': {},
            }
        },
        's3_bucket_path': 'maven2/org/mozilla/geckoview-beta-x86/62.0b3/',
    },
    {},
    True,
)))
def test_get_maven_expected_files_per_archive_per_task_id(upstream_artifacts_per_task_id, mapping_manifest, expected, raises):
    if raises:
        with pytest.raises(ValueError):
            get_maven_expected_files_per_archive_per_task_id(upstream_artifacts_per_task_id, mapping_manifest)
    else:
        assert get_maven_expected_files_per_archive_per_task_id(
            upstream_artifacts_per_task_id, mapping_manifest
        ) == expected
