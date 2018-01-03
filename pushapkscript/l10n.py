_EXPECTED_L10N_STRINGS_FILE_NAME = 'public/google_play_strings.json'


def get_google_play_strings_path(context, artifacts_per_task_id, failed_artifacts_per_task_id):
    if failed_artifacts_per_task_id:
        if len(failed_artifacts_per_task_id) > 1:
            raise Exception('Only 1 task can fail. Found: {}'.format())

        task_id = list(failed_artifacts_per_task_id.keys())[0]
        failed_artifacts = failed_artifacts_per_task_id[task_id]
        if len(failed_artifacts) > 1:
            raise Exception('More than one artifact failed for taskId "{}": {}'.format(task_id, failed_artifacts))
        if _EXPECTED_L10N_STRINGS_FILE_NAME not in failed_artifacts:
            raise Exception('Could not find "{}". Found: {}'.format(_EXPECTED_L10N_STRINGS_FILE_NAME, failed_artifacts))

        return None

    return _find_unique_google_play_strings_file_in_dict(artifacts_per_task_id)


def _find_unique_google_play_strings_file_in_dict(artifact_dict):
    l10n_strings_paths = [
        path
        for task_id, paths in artifact_dict.items()
        for path in paths
        if _EXPECTED_L10N_STRINGS_FILE_NAME in path
    ]

    number_of_artifacts_found = len(l10n_strings_paths)
    if number_of_artifacts_found == 0:
        raise Exception('Could not find "{}" in: {}'.format(_EXPECTED_L10N_STRINGS_FILE_NAME, artifact_dict))
    if number_of_artifacts_found > 1:
        raise Exception('More than one artifact "{}" found: {}'.format(_EXPECTED_L10N_STRINGS_FILE_NAME, l10n_strings_paths))

    return l10n_strings_paths[0]
