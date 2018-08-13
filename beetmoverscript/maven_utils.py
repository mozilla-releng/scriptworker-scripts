import os

_MAVEN_ZIP_NAME = 'target.maven.zip'


def get_maven_expected_files_per_archive_per_task_id(upstream_artifacts_per_task_id, mapping_manifest):
    task_id, maven_zip_full_path = _get_task_id_and_full_path_of_maven_archive(upstream_artifacts_per_task_id)

    return {
        task_id: {
            maven_zip_full_path: _get_maven_expected_files_in_archive(mapping_manifest)
        }
    }


def _get_task_id_and_full_path_of_maven_archive(upstream_artifacts_per_task_id):
    candidate_task_id = ''
    candidate_path = ''

    for task_id, upstream_definitions in upstream_artifacts_per_task_id.items():
        for upstream_definition in upstream_definitions:
            for path in upstream_definition['paths']:
                if path.endswith(_MAVEN_ZIP_NAME):
                    if candidate_task_id:
                        raise ValueError(
                            'Too many upstream artifact ending with "{}" found: ({}, {}) and ({}, {})'.format(
                                _MAVEN_ZIP_NAME, candidate_task_id, candidate_path, task_id, path
                            )
                        )

                    candidate_task_id = task_id
                    candidate_path = path

    if not candidate_task_id:
        raise ValueError('No upstream artifact ending with "{}" found. Given: {}'.format(
            _MAVEN_ZIP_NAME, upstream_artifacts_per_task_id)
        )

    return candidate_task_id, candidate_path


def _get_maven_expected_files_in_archive(mapping_manifest):
    files = mapping_manifest['mapping']['en-US'].keys()
    return [
        os.path.join(
            _remove_first_directory_from_bucket(mapping_manifest['s3_bucket_path']),
            file
        ) for file in files
    ]


def _remove_first_directory_from_bucket(s3_bucket_path):
    # remove 'maven2' because it's not in the archive, but it exists on the maven server
    return '/'.join(s3_bucket_path.split('/')[1:])
