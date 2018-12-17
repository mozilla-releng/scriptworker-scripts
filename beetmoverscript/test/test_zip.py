import contextlib
import os
import pytest
import tempfile
import zipfile

from pathlib import Path
from scriptworker.exceptions import TaskVerificationError

from beetmoverscript.zip import (
    check_and_extract_zip_archives,
    _check_and_extract_zip_archives_for_given_task,
    _check_extract_and_delete_zip_archive,
    _check_archive_itself,
    _fetch_zip_metadata,
    _ensure_files_in_archive_have_decent_sizes,
    _ensure_all_expected_files_are_present_in_archive,
    _extract_and_check_output_files,
    _ensure_all_expected_files_are_deflated_on_disk,
    _ensure_no_file_got_overwritten,
)


def _create_zip(in_folder, files_and_content, archive_name='some_archive.zip'):
    archive_path = os.path.join(in_folder, archive_name)
    with zipfile.ZipFile(archive_path, mode='w') as zip:
        for file_name_in_archive, content in files_and_content.items():
            with tempfile.NamedTemporaryFile(mode='w+') as temp_file:
                temp_file.write(content)
                temp_file.seek(0)
                zip.write(temp_file.name, file_name_in_archive)

    return archive_path


def test_check_and_extract_zip_archives():
    first_task_id_archive1_files_and_content = {
        'some_file1': 'some content 1',
        'some/subfolder/file1': 'some other content 1',
    }
    first_task_id_archive2_files_and_content = {
        'some_file2': 'some content 2',
        'some/subfolder/file2': 'some other content 2',
    }
    third_task_id_archive1_files_and_content = {
        'some_file3': 'some content 3',
        'some/subfolder/file3': 'some other content 3',
    }

    with tempfile.TemporaryDirectory() as d:
        first_task_id_archive1_path = _create_zip(
            d, first_task_id_archive1_files_and_content, archive_name='firstTaskId-archive1.zip'
        )
        first_task_id_archive2_path = _create_zip(
            d, first_task_id_archive2_files_and_content, archive_name='firstTaskId-archive2.zip'
        )
        third_task_id_archive1_path = _create_zip(
            d, third_task_id_archive1_files_and_content, archive_name='thirdTaskId-archive1.zip'
        )

        artifacts_per_task_id = {
            'firstTaskId': [{
                'paths': ['/a/non/archive', '/another/non/archive'],
                'zip_extract': False,
            }, {
                'paths': [first_task_id_archive1_path, first_task_id_archive2_path],
                'zip_extract': True,
            }],
            'secondTaskId': [{
                'paths': ['/just/another/regular/file'],
                'zip_extract': False,
            }],
            'thirdTaskId': [{
                'paths': [third_task_id_archive1_path],
                'zip_extract': True,
            }],
        }

        expected_files_per_archive_per_task_id = {
            'firstTaskId': {
                first_task_id_archive1_path: list(first_task_id_archive1_files_and_content.keys()),
                first_task_id_archive2_path: list(first_task_id_archive2_files_and_content.keys()),
            },
            'thirdTaskId': {
                third_task_id_archive1_path: list(third_task_id_archive1_files_and_content.keys()),
            },
        }

        mapping_manifest = {'s3_bucket_path': 'dummy'}
        files_once_extracted = check_and_extract_zip_archives(
            artifacts_per_task_id, expected_files_per_archive_per_task_id,
            zip_max_size_in_mb=100, mapping_manifest=mapping_manifest,
        )

        assert files_once_extracted == {
            os.path.join(d, 'firstTaskId-archive1.zip'): {
                'some_file1': os.path.join(d, 'firstTaskId-archive1.zip.out', 'some_file1'),
                'some/subfolder/file1': os.path.join(d, 'firstTaskId-archive1.zip.out', 'some', 'subfolder', 'file1'),
            },
            os.path.join(d, 'firstTaskId-archive2.zip'): {
                'some_file2': os.path.join(d, 'firstTaskId-archive2.zip.out', 'some_file2'),
                'some/subfolder/file2': os.path.join(d, 'firstTaskId-archive2.zip.out', 'some', 'subfolder', 'file2'),
            },
            os.path.join(d, 'thirdTaskId-archive1.zip'): {
                'some_file3': os.path.join(d, 'thirdTaskId-archive1.zip.out', 'some_file3'),
                'some/subfolder/file3': os.path.join(d, 'thirdTaskId-archive1.zip.out', 'some', 'subfolder', 'file3'),
            },
        }


def test_check_and_extract_zip_archives_for_given_task():
    archive1_files_and_content = {
        'some_file1': 'some content 1',
        'some/subfolder/file1': 'some other content 1',
    }
    archive2_files_and_content = {
        'some_file2': 'some content 2',
        'some/subfolder/file2': 'some other content 2',
    }

    with tempfile.TemporaryDirectory() as d:
        archive1_path = _create_zip(d, archive1_files_and_content, archive_name='archive1.zip')
        archive2_path = _create_zip(d, archive2_files_and_content, archive_name='archive2.zip')

        expected_files_per_archive = {
            archive1_path: ['some_file1', 'some/subfolder/file1'],
            archive2_path: ['some_file2', 'some/subfolder/file2'],
        }

        mapping_manifest = {'s3_bucket_path': 'dummy'}
        extracted_files = _check_and_extract_zip_archives_for_given_task(
            'someTaskId', expected_files_per_archive, zip_max_size_in_mb=100,
            mapping_manifest=mapping_manifest
        )

        assert extracted_files == {
            os.path.join(d, 'archive1.zip'): {
                'some_file1': os.path.join(d, 'archive1.zip.out', 'some_file1'),
                'some/subfolder/file1': os.path.join(d, 'archive1.zip.out', 'some', 'subfolder', 'file1'),
            },
            os.path.join(d, 'archive2.zip'): {
                'some_file2': os.path.join(d, 'archive2.zip.out', 'some_file2'),
                'some/subfolder/file2': os.path.join(d, 'archive2.zip.out', 'some', 'subfolder', 'file2'),
            },
        }


def test_check_extract_and_delete_zip_archive():
    files_and_content = {
        'some_file': 'some content',
        'some/subfolder/file': 'some other content',
    }

    with tempfile.TemporaryDirectory() as d:
        archive_path = _create_zip(d, files_and_content)
        mapping_manifest = {'s3_bucket_path': 'dummy'}
        extracted_files = _check_extract_and_delete_zip_archive(
            archive_path, files_and_content.keys(), zip_max_size_in_mb=100,
            mapping_manifest=mapping_manifest
        )
        assert extracted_files == {
            'some_file': os.path.join(d, 'some_archive.zip.out', 'some_file'),
            'some/subfolder/file': os.path.join(d, 'some_archive.zip.out', 'some/subfolder/file'),
        }
        for file in extracted_files.values():
            assert os.path.exists(file)
            assert os.path.isfile(file)
            key = [f for f in files_and_content.keys() if file.endswith(f)][0]
            with open(file) as f:
                assert f.read() == files_and_content[key]

        assert not os.path.exists(archive_path)


@pytest.mark.parametrize('file_size_in_mb, is_zip, zip_max_size_in_mb, raises', (
    (1, True, 2, False),
    (3, True, 2, True),
    (3, True, 4, False),
    (1, False, 2, True),
))
def test_check_archive_itself(file_size_in_mb, is_zip, zip_max_size_in_mb, raises):
    with tempfile.TemporaryDirectory() as d:
        file_path = os.path.join(d, 'some_file')
        with open(file_path, mode='wb') as f:
            f.write(b'a' * (file_size_in_mb * 1024 * 1024))

        archive_path = os.path.join(d, 'some_archive')

        if is_zip:
            with zipfile.ZipFile(archive_path, mode='w') as zip:   # default does not compress data
                zip.write(file_path)
        else:
            archive_path = file_path

        if raises:
            with pytest.raises(TaskVerificationError):
                _check_archive_itself(archive_path, zip_max_size_in_mb)
        else:
            _check_archive_itself(archive_path, zip_max_size_in_mb)


def test_fetch_zip_metadata():
    with tempfile.NamedTemporaryFile(mode='w+b') as f:
        with zipfile.ZipFile(f.name, mode='w', compression=zipfile.ZIP_BZIP2) as zip_file:
            with tempfile.NamedTemporaryFile(mode='w') as f1:
                f1.write('some content that is 32-byte-big')
                f1.seek(0)
                zip_file.write(f1.name, arcname='some_file')

            with tempfile.NamedTemporaryFile(mode='w') as f2:
                f2.write('some other content that is 38-byte-big')
                f2.seek(0)
                zip_file.write(f2.name, arcname='some/subdir/some_other_file')

        with zipfile.ZipFile(f.name, mode='r') as zip_file:
            assert _fetch_zip_metadata(zip_file) == {
                'some_file': {
                    'compress_size': 67,
                    'file_size': 32,
                },
                'some/subdir/some_other_file': {
                    'compress_size': 72,
                    'file_size': 38,
                }
            }


@pytest.mark.parametrize('zip_metadata, zip_max_size_in_mb, raises', ((
    {
        'file1': {
            'compress_size': 1000,
            'file_size': 1000,
        },
        'file2': {
            'compress_size': 1000,
            'file_size': 2000,
        },
    },
    100,
    False,
), (
    {
        'file1': {
            'compress_size': 101 * 1024 * 1024,
            'file_size': 101 * 1024 * 1024,
        },
    },
    100,
    True,
), (
    {
        'file1': {
            'compress_size': 2 * 1024 * 1024,
            'file_size': 2 * 1024 * 1024,
        },
    },
    1,
    True,
), (
    {
        'file1': {
            'compress_size': 100,
            'file_size': 1 * 1024 * 1024,
        },
    },
    100,
    True,
), (
    {
        'file1': {
            'compress_size': 50,
            'file_size': 10,    # Can happen with small files
        },
    },
    100,
    False,
)))
def test_ensure_files_in_archive_have_decent_sizes(zip_metadata, zip_max_size_in_mb, raises):
    if raises:
        with pytest.raises(TaskVerificationError):
            _ensure_files_in_archive_have_decent_sizes('/some/archive.zip', zip_metadata, zip_max_size_in_mb)
    else:
        _ensure_files_in_archive_have_decent_sizes('/some/archive.zip', zip_metadata, zip_max_size_in_mb)


@pytest.mark.parametrize('files_in_archive, expected_files, mapping_manifest, raises', ((
    ['some_file', 'some/other/file'],
    ['some_file', 'some/other/file'],
    {'s3_bucket_path': 'dummy'},
    False,
), (
    ['/some/absolute/path'],
    ['/some/absolute/file'],
    {'s3_bucket_path': 'dummy'},
    True,
), (
    ['some/.///redundant/path'],
    ['some/.///redundant/path'],
    {'s3_bucket_path': 'dummy'},
    True,
), (
    ['some/../../../etc/passwd'],
    ['some/../../../etc/passwd'],
    {'s3_bucket_path': 'dummy'},
    True,
), (
    ['some_file', 'some_wrong_file'],
    ['some_file', 'some_other_file'],
    {'s3_bucket_path': 'dummy'},
    True,
), (
    ['some_file'],
    ['some_file', 'some_missing_file'],
    {'s3_bucket_path': 'dummy'},
    True,
), (
    ['some_file', 'some_unexpected_file'],
    ['some_file'],
    {'s3_bucket_path': 'dummy'},
    True,
), (
    ['some_duplicated_file', 'some_duplicated_file'],
    ['some_duplicated_file', 'some_duplicated_file'],
    {'s3_bucket_path': 'dummy'},
    True,
), (
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20181129.145599-1.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20189929.145558-1.aar.sha1',
    ],
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.aar.sha1',
    ],
    {'s3_bucket_path': 'dummy-SNAPSHOT'},
    True,
), (
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-2018INVALID1129.145558-1.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20181129.MIXED-1.aar.sha1',
    ],
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.aar.sha1',
    ],
    {'s3_bucket_path': 'dummy-SNAPSHOT'},
    True,
), (
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-020181129.145558-1.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20181129.-failure.aar.sha1',
    ],
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.aar.sha1',
    ],
    {'s3_bucket_path': 'dummy-SNAPSHOT'},
    True,
), (
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20181129.145558-1.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20181130.145558-1.aar.sha1',
    ],
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.pom',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}.aar.sha1',
    ],
    {'s3_bucket_path': 'dummy-SNAPSHOT'},
    True,
), (
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20181129.145558-1-sources.jar',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-20181129.145558-1-sources.jar.md5',
    ],
    [
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar',
        'org/mzl/components/browser-awesomebar/X.Y.Z-SNAPSHOT/browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar.md5',
    ],
    {
        's3_bucket_path': 'dummy-SNAPSHOT',
        'mapping': {
            'en-US': {
                'browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar': {
                    'destinations': [
                        'browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar'
                    ],
                    's3_key': 'browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar',
                },
                'browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar.md5': {
                    'destinations': [
                        'browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar.md5'
                    ],
                    's3_key': 'browser-awesomebar-X.Y.Z-{{date_timestamp}}.{{clock_timestamp}}-{{build_number}}-sources.jar.md5'
                }
            }
        }
    },
    False,
)))
def test_ensure_all_expected_files_are_present_in_archive(files_in_archive,
                                                          expected_files,
                                                          mapping_manifest,
                                                          raises):
    if raises:
        with pytest.raises(TaskVerificationError):
            _ensure_all_expected_files_are_present_in_archive('/some/archive.zip', files_in_archive,
                                                              expected_files, mapping_manifest)
    else:
        _ensure_all_expected_files_are_present_in_archive('/some/archive.zip', files_in_archive,
                                                          expected_files, mapping_manifest)


def test_extract_and_check_output_files():
    with tempfile.TemporaryDirectory() as d:
        zip_path = os.path.join(d, 'some.zip')

        file1 = os.path.join(d, 'some_file')
        with open(file1, mode='w') as f:
            f.write('some content')

        file2 = os.path.join(d, 'some_other_file')
        with open(file2, mode='w') as f:
            f.write('some other content')

        with zipfile.ZipFile(zip_path, mode='w') as zip_file:
            zip_file.write(file1, arcname='some_file')
            zip_file.write(file2, arcname='some/subfolder/file')

        os.remove(file1)
        os.remove(file2)

        extracted_file1 = os.path.join(d, 'some.zip.out', 'some_file')
        extracted_file2 = os.path.join(d, 'some.zip.out', 'some', 'subfolder', 'file')
        expected_extracted_files = {
            'some_file': extracted_file1,
            'some/subfolder/file': extracted_file2,
        }

        with zipfile.ZipFile(zip_path, mode='r') as zip_file:
            assert _extract_and_check_output_files(
                zip_file, ['some_file', 'some/subfolder/file']
            ) == expected_extracted_files

        with open(extracted_file1) as f:
            assert f.read() == 'some content'

        with open(extracted_file2) as f:
            assert f.read() == 'some other content'


@contextlib.contextmanager
def cwd(new_cwd):
    current_dir = os.getcwd()
    try:
        os.chdir(new_cwd)
        yield
    finally:
        os.chdir(current_dir)


def test_fail_extract_and_check_output_files():
    zip_path = 'relative/path/to/some.zip'

    with tempfile.TemporaryDirectory() as d:
        with cwd(d):
            os.makedirs(os.path.join(d, 'relative/path/to'))
            with zipfile.ZipFile(zip_path, mode='w') as zip_file:
                pass

            with zipfile.ZipFile(zip_path, mode='r') as zip_file:
                with pytest.raises(TaskVerificationError):
                    _extract_and_check_output_files(zip_file, ['some_file', 'some/subfolder/file'])


def test_ensure_all_expected_files_are_deflated_on_disk():
    with tempfile.TemporaryDirectory() as d:
        folder = os.path.join(d, 'some/folder')
        os.makedirs(folder)
        file1 = os.path.join(folder, 'some_file')
        file2 = os.path.join(folder, 'some_other_file')
        Path(file1).touch()
        Path(file2).touch()

        _ensure_all_expected_files_are_deflated_on_disk('/path/to/zip', [file1, file2])


def test_fail_ensure_all_expected_files_are_deflated_on_disk():
    with tempfile.TemporaryDirectory() as d:
        folder = os.path.join(d, 'some/folder')
        os.makedirs(folder)
        non_existing_path = os.path.join(folder, 'non_existing_path')

        with pytest.raises(TaskVerificationError):
            _ensure_all_expected_files_are_deflated_on_disk('/path/to/zip', [non_existing_path])

        with pytest.raises(TaskVerificationError):
            _ensure_all_expected_files_are_deflated_on_disk('/path/to/zip', [folder])


@pytest.mark.parametrize('files, raises', (
    (['/some/file'], False),
    (['/some/file', '/some/other_file'], False),
    (['/some/file', '/some/other_file', '/some/file'], True),
))
def test_ensure_no_file_got_overwritten(files, raises):
    if raises:
        with pytest.raises(TaskVerificationError):
            _ensure_no_file_got_overwritten('someTaskId', files)
    else:
        _ensure_no_file_got_overwritten('someTaskId', files)
