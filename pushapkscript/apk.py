from zipfile import ZipFile

from pushapkscript.exceptions import TaskVerificationError
from pushapkscript.utils import filter_out_identical_values


_DIRECTORY_WITH_ARCHITECTURE_METADATA = 'lib/'     # For instance: lib/x86/ or lib/armeabi-v7a/
_ARCHITECTURE_SUBDIRECTORY_INDEX = len(_DIRECTORY_WITH_ARCHITECTURE_METADATA.split('/')) - 1    # Removes last trailing slash

_EXPECTED_MOZAPKPUBLISHER_ARCHITECTURES_PER_CHANNEL = {
    # XXX arm64-v8a to come in Aurora (Bug 1368484)
    'aurora': ('armv7_v15', 'x86'),
    'beta': ('armv7_v15', 'x86'),
    'release': ('armv7_v15', 'x86'),
}


def sort_and_check_apks_per_architectures(apks_paths, channel):
    apks_per_architectures = {
        _convert_architecture_to_mozapkpublisher(_get_apk_architecture(apk_path)): apk_path
        for apk_path in apks_paths
    }

    _check_architectures_are_valid(apks_per_architectures.keys(), channel)

    return apks_per_architectures


def _convert_architecture_to_mozapkpublisher(architecture):
    return 'armv7_v15' if architecture == 'armeabi-v7a' else architecture


def _get_apk_architecture(apk_path):
    with ZipFile(apk_path) as apk_zip:
        files_with_architecture_in_path = [
            file_info.filename for file_info in apk_zip.infolist()
            if _DIRECTORY_WITH_ARCHITECTURE_METADATA in file_info.filename
        ]

    if not files_with_architecture_in_path:
        raise TaskVerificationError('"{}" does not contain a directory called "{}"'
                                    .format(apk_path, _DIRECTORY_WITH_ARCHITECTURE_METADATA))

    return _extract_architecture_from_paths(apk_path, files_with_architecture_in_path)


def _extract_architecture_from_paths(apk_path, paths):
    detected_architectures = [
        path.split('/')[_ARCHITECTURE_SUBDIRECTORY_INDEX] for path in paths
    ]
    unique_architectures = filter_out_identical_values(detected_architectures)
    non_empty_unique_architectures = [
        architecture for architecture in unique_architectures if architecture
    ]
    number_of_unique_architectures = len(non_empty_unique_architectures)

    if number_of_unique_architectures == 0:
        raise TaskVerificationError('"{}" does not contain any architecture data under these paths: {}'.format(apk_path, paths))
    elif number_of_unique_architectures > 1:
        raise TaskVerificationError('"{}" contains too many architures: {}'.format(apk_path, unique_architectures))

    return unique_architectures[0]


def _check_architectures_are_valid(mozapkpublisher_architectures, channel):
    try:
        expected_architectures = _EXPECTED_MOZAPKPUBLISHER_ARCHITECTURES_PER_CHANNEL[channel]
    except KeyError:
        raise TaskVerificationError('"{}" is not an expected channel. Allowed values: {}'.format(
            channel, _EXPECTED_MOZAPKPUBLISHER_ARCHITECTURES_PER_CHANNEL.keys()
        ))

    are_all_architectures_present = all(
        expected_architecture in mozapkpublisher_architectures
        for expected_architecture in expected_architectures
    )

    if not are_all_architectures_present:
        raise TaskVerificationError('One or many architecture are missing. Detected architectures: {}. Expected architecture: {}'
                                    .format(mozapkpublisher_architectures, expected_architectures))

    if len(mozapkpublisher_architectures) > len(expected_architectures):
        raise TaskVerificationError('Unsupported architectures detected. Detected architectures: {}. Expected architecture: {}'
                                    .format(mozapkpublisher_architectures, expected_architectures))
