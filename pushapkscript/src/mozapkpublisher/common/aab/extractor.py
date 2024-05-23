import logging
import os
import shutil
import subprocess
import tempfile


logger = logging.getLogger(__name__)


def extract_metadata(aab_path):
    logger.info('Extracting metadata from "{}"...'.format(aab_path))
    metadata = {}

    with tempfile.NamedTemporaryFile() as aab_copy:
        shutil.copy(aab_path, aab_copy.name)
        aab_copy.seek(0)

        metadata['package_name'] = _extract_package_name(aab_copy.name)
        logger.info('Found package name "{}"'.format(metadata['package_name']))
        metadata['version_code'] = _extract_version_code(aab_copy.name)
        logger.info('Found version code "{}"'.format(metadata['version_code']))

    return metadata


def _run_bundletool(bundletool_args):
    bundletool_path = os.environ.get("BUNDLETOOL_PATH", "./bundletool.jar")
    cmd = ['java', '-jar', bundletool_path] + bundletool_args
    logger.debug(f'Running command: {cmd}')
    out = subprocess.check_output(cmd, text=True)
    out = out.strip('\n')
    logger.debug(f'Output: {out}')
    return out


def _extract_package_name(aab_path):
    args = ['dump', 'manifest', f'--bundle={aab_path}', '--xpath=/manifest/@package']
    out = _run_bundletool(args)
    return out


def _extract_version_code(aab_path):
    args = ['dump', 'manifest', f'--bundle={aab_path}', '--xpath=/manifest/@android:versionCode']
    out = _run_bundletool(args)
    return out
