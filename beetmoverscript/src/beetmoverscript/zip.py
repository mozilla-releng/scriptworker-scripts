import datetime
import logging
import os
import re
import zipfile

from scriptworker.exceptions import TaskVerificationError

from beetmoverscript.constants import (
    ZIP_MAX_COMPRESSION_RATIO, SNAPSHOT_TIMESTAMP_REGEX
)
from beetmoverscript.utils import JINJA_ENV

log = logging.getLogger(__name__)


def check_and_extract_zip_archives(artifacts_per_task_id,
                                   expected_files_per_archive_per_task_id,
                                   zip_max_size_in_mb,
                                   mapping_manifest):
    """Verify zip archives and extract them.

    This function enhances the checks done in python's zipfile. Each of the zip file passed is
    checked before attempting any extraction. The archives themselves are ensure to be not too big
    (less than `zip_max_size_in_mb`) and to be actual zip files. Then, the content is verified.
    Each file within an archive must not be too big (less than `zip_max_size_in_mb`) and must not
    have a too high compression ratio (less than `ZIP_MAX_COMPRESSION_RATIO`). File names are
    ensure to be relative paths (no full paths allowed) and to not contain any up references (`..`).
    Then, the file list is matched against the expected one (given in
    `expected_files_per_archive_per_task_id`). No file must be missing. None must be found extra.
    If any of these condition is not met, then the function raises an exception, without attempting
    to extract the files.

    Otherwise, files are extracted in the same folder as the zip archive, under the subfolder
    named after the archive name: `x.out` x being the name of the archive including the extension.
    Finally, all expected files are checked to exist on disk, to ensure none got overwritten.

    Args:
        artifacts_per_task_id (dict): a dictionary keyed by taskId. Value is a list of dictionaries
        matching the schema `{'paths': list(str), 'zip_extract': bool}`. Any path with `zip_extract`
        being false will be ignored and not returned in the list of deflated artifacts.

        expected_files_per_archive_per_task_id (dict): a dictionary keyed by taskId. Value is
        another dictionary keyed by the full path of the archive. Value is then a list of relative
        paths of expected files in the archive

        zip_max_size_in_mb (int): if an archive or a file within the archive is bigger than this
        value, then the archive is considered invalid.

        mapping_manifest (dict): a dictionary keyed by artifact name.

    Raises:
        TaskVerificationError: whenever an archive breaks one of the rules stated above

    Returns:
        dict: A dictionary keyed by the full path of the archive. Value is another dictionary keyed
        by relative path of files in the archve. Value is the full path of the extracted file.
    """

    deflated_artifacts = {}

    for task_id, task_artifacts_params in artifacts_per_task_id.items():
        for artifacts_param in task_artifacts_params:
            if artifacts_param['zip_extract'] is False:
                log.debug('Skipping artifacts marked as not `zipExtract`able: {}'.format(artifacts_param['paths']))
                continue

            expected_files_per_archive = expected_files_per_archive_per_task_id[task_id]
            # No need to key deflated_artifacts by task_id. task_id is already in the full path of the archive
            deflated_artifacts.update(_check_and_extract_zip_archives_for_given_task(
                task_id, expected_files_per_archive, zip_max_size_in_mb, mapping_manifest
            ))

    log.info('Extracted these files: {}'.format(deflated_artifacts))

    return deflated_artifacts


def _check_and_extract_zip_archives_for_given_task(task_id, expected_files_per_archive,
                                                   zip_max_size_in_mb, mapping_manifest):
    extracted_files = {}

    for archive_path, expected_files in expected_files_per_archive.items():
        log.info('Processing archive "{}" which marked as `zipExtract`able'.format(archive_path))
        extracted_files[archive_path] = _check_extract_and_delete_zip_archive(
            archive_path, expected_files, zip_max_size_in_mb, mapping_manifest
        )

    # We make this check at this stage (and not when all files from all tasks got extracted)
    # because files from different tasks are stored in different folders by scriptworker. Moreover
    # we tested no relative paths like ".." were used within the archive.
    _ensure_no_file_got_overwritten(task_id, extracted_files)

    return extracted_files


def _check_extract_and_delete_zip_archive(zip_path, expected_files,
                                          zip_max_size_in_mb, mapping_manifest):
    _check_archive_itself(zip_path, zip_max_size_in_mb)

    with zipfile.ZipFile(zip_path) as zip_file:
        zip_metadata = _fetch_zip_metadata(zip_file)
        relative_paths_in_archive = list(zip_metadata.keys())

        # we don't close the file descriptor here to avoid the tested file to be swapped by a rogue one
        _ensure_files_in_archive_have_decent_sizes(zip_path, zip_metadata, zip_max_size_in_mb)
        _ensure_all_expected_files_are_present_in_archive(zip_path, relative_paths_in_archive,
                                                          expected_files, mapping_manifest)
        log.info('Content of archive "{}" is sane'.format(zip_path))

        extracted_files = _extract_and_check_output_files(zip_file, relative_paths_in_archive)

    # We remove the zip archive because it's not used anymore. We just need the deflated files
    os.remove(zip_path)
    log.debug('Deleted archive "{}"'.format(zip_path))

    return extracted_files


def _check_archive_itself(zip_path, zip_max_size_in_mb):
    zip_size = os.path.getsize(zip_path)
    zip_size_in_mb = zip_size // (1024 * 1024)

    if zip_size_in_mb > zip_max_size_in_mb:
        raise TaskVerificationError(
            'Archive "{}" is too big. Max accepted size (in MB): {}. File size (in MB): {}'.format(
                zip_path, zip_max_size_in_mb, zip_size_in_mb
            )
        )

    if not zipfile.is_zipfile(zip_path):
        raise TaskVerificationError(
            'Archive "{}" is not a valid zip file.'
        )

    log.info('Structure of archive "{}" is sane'.format(zip_path))


def _fetch_zip_metadata(zip_file):
    return {
        info.filename: {
            'compress_size': info.compress_size,
            'file_size': info.file_size,
        }
        # TODO: we should add a check following up this filtering to ensure no
        # empty dirs were created
        for info in zip_file.infolist() if not info.is_dir()
    }


def _ensure_files_in_archive_have_decent_sizes(zip_path, zip_metadata, zip_max_size_in_mb):
    for file_name, file_metadata in zip_metadata.items():
        compressed_size = file_metadata['compress_size']
        real_size = file_metadata['file_size']
        compressed_size_size_in_mb = compressed_size // (1024 * 1024)

        if compressed_size_size_in_mb > zip_max_size_in_mb:
            raise TaskVerificationError(
                'In archive "{}", compressed file "{}" is too big. Max accepted size (in MB): {}. File size (in MB): {}'.format(
                    zip_path, file_name, zip_max_size_in_mb, compressed_size_size_in_mb
                )
            )

        compression_ratio = real_size / compressed_size
        if compression_ratio > ZIP_MAX_COMPRESSION_RATIO:
            raise TaskVerificationError(
                'In archive "{}", file "{}" has a suspicious compression ratio. Max accepted: {}. Found: {}'.format(
                    zip_path, file_name, ZIP_MAX_COMPRESSION_RATIO, compression_ratio
                )
            )

    log.info('Archive "{}" contains files with legitimate sizes.'.format(zip_path))


def _ensure_all_expected_files_are_present_in_archive(zip_path, files_in_archive,
                                                      expected_files, mapping_manifest):
    files_in_archive = set(files_in_archive)

    unique_expected_files = set(expected_files)
    if len(expected_files) != len(unique_expected_files):
        duplicated_files = [file for file in unique_expected_files if expected_files.count(file) > 1]
        raise TaskVerificationError(
            'Found duplicated expected files in archive "{}": {}'.format(zip_path, duplicated_files)
        )

    identifiers_collection = []
    rendered_unique_expected_files = unique_expected_files
    _args = {}

    for file_ in files_in_archive:
        if os.path.isabs(file_):
            raise TaskVerificationError(
                'File "{}" in archive "{}" cannot be an absolute one.'.format(file_, zip_path)
            )
        if os.path.normpath(file_) != file_:
            raise TaskVerificationError(
                'File "{}" in archive "{}" cannot contain up-level reference nor redundant separators'.format(
                    file_, zip_path
                )
            )
        if mapping_manifest and 'SNAPSHOT' in mapping_manifest['s3_bucket_path']:
            (date, clock, bno) = _extract_and_check_timestamps(file_,
                                                               SNAPSHOT_TIMESTAMP_REGEX)
            _args = {
                'date_timestamp': date,
                'clock_timestamp': clock,
                'build_number': bno
            }
            # reload the unique_expected_files with their corresponding values
            # by rendering them via Jinja2 variables
            rendered_unique_expected_files = set([
                JINJA_ENV.from_string(f).render(**_args) for f in unique_expected_files
            ])
            identifiers_collection.append(frozenset(_args.items()))
        if file_ not in rendered_unique_expected_files:
            raise TaskVerificationError(
                'File "{}" present in archive "{}" is not expected. Expected: {}'.format(
                    file_, zip_path, unique_expected_files
                )
            )
    identifiers_collection_set = set(identifiers_collection)
    if len(identifiers_collection_set) > 1:
        # bail if there are different timestamps or buildnumbers across the same
        # target.maven.zip files
        raise TaskVerificationError(
            'Different buildnumbers/timestamps identified within the archive {}'.format(
                zip_path
            )
        )
    elif len(identifiers_collection_set) == 1:
        # use this unique identifier per artifacts_id zip archive to munge and
        # populate the mapping_manifest
        for locale, value in mapping_manifest['mapping'].items():
            mapping_manifest['mapping'][locale] = render_dict(value, _args)

    if len(files_in_archive) != len(unique_expected_files):
        missing_expected_files = [file for file in unique_expected_files if file not in files_in_archive]
        raise TaskVerificationError(
            'Expected files are missing in archive "{}": {}'.format(zip_path, missing_expected_files)
        )

    log.info('Archive "{}" contains all expected files: {}'.format(zip_path, unique_expected_files))


def render_dict(d, kwargs):
    """ Function to render a nested Python-dict structure to fill in all Jinja2
    variables"""
    def render_dict_(string, dict_to_render):
        """ Function to render any Jinja2 variables for a given string"""
        return JINJA_ENV.from_string(string).render(**dict_to_render)

    rendered_dict = {}
    for artifact_name, artifact_info in d.items():
        rendered_dict[render_dict_(artifact_name, kwargs)] = {
            'destinations': [render_dict_(x, kwargs) for x in artifact_info['destinations']],
            's3_key': render_dict_(artifact_info['s3_key'], kwargs),
        }
    return rendered_dict


def _extract_and_check_timestamps(archive_filename, regex):
    match = re.search(regex, archive_filename)
    try:
        identifier = match.group()
    except AttributeError:
        raise TaskVerificationError(
            'File "{}" present in archive has invalid identifier. '
            'Expected YYYYMMDD.HHMMSS-BUILDNUMBER within in'.format(
                archive_filename
            )
        )
    timestamp, build_number = identifier.split('-')
    try:
        datetime.datetime.strptime(timestamp, '%Y%m%d.%H%M%S')
    except ValueError:
        raise TaskVerificationError(
            'File "{}" present in archive has invalid timestamp. '
            'Expected YYYYMMDD.HHMMSS within in'.format(
                archive_filename
            )
        )

    date_timestamp, clock_timestamp = timestamp.split('.')
    return date_timestamp, clock_timestamp, build_number


def _extract_and_check_output_files(zip_file, relative_path_in_archive):
    zip_path = zip_file.filename

    if not os.path.isabs(zip_path):
        raise TaskVerificationError(
            'Archive "{}" is not absolute path. Cannot know where to extract content'.format(zip_path)
        )

    extract_to = '{}.out'.format(zip_path)
    expected_full_paths_per_relative_path = {
        path_in_archive: os.path.join(extract_to, path_in_archive)
        for path_in_archive in relative_path_in_archive
    }
    log.info('Extracting archive "{}" to "{}"...'.format(zip_path, extract_to))
    zip_file.extractall(extract_to)
    log.info('Extracted archive "{}". Verfiying extracted data...'.format(zip_path, extract_to))

    _ensure_all_expected_files_are_deflated_on_disk(zip_path, expected_full_paths_per_relative_path.values())

    return expected_full_paths_per_relative_path


def _ensure_all_expected_files_are_deflated_on_disk(zip_path, expected_full_paths):
    for full_path in expected_full_paths:
        if not os.path.exists(full_path):
            raise TaskVerificationError(
                'After extracting "{}", expected file "{}" does not exist'.format(zip_path, full_path)
            )
        if not os.path.isfile(full_path):
            raise TaskVerificationError(
                'After extracting "{}", "{}" is not a file'.format(zip_path, full_path)
            )

    log.info('All files declared in archive "{}" exist and are regular files: {}'.format(
        zip_path, expected_full_paths
    ))


def _ensure_no_file_got_overwritten(task_id, extracted_files):
    unique_paths = set(extracted_files)

    if len(unique_paths) != len(extracted_files):
        duplicated_paths = [path for path in unique_paths if extracted_files.count(path) > 1]
        raise TaskVerificationError(
            'Archives from task "{}" overwrote files: {}'.format(task_id, duplicated_paths)
        )

    log.info('All archives from task "{}" outputed different files.'.format(task_id))
