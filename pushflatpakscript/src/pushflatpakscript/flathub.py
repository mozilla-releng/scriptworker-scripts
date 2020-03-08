import logging
import os
import subprocess
import tarfile

from scriptworker.exceptions import TaskVerificationError

from pushflatpakscript import task
from pushflatpakscript.constants import TAR_MAX_SIZE_IN_MB

log = logging.getLogger(__name__)

FLATAHUB_API_RESPONSE_PREFIX = "{flathub_url}api/v1/build/"


def validate_publish_build_output(context, content):
    prefix = FLATAHUB_API_RESPONSE_PREFIX.format(flathub_url=context.config["flathub_url"])
    if not content.startswith(prefix):
        raise TaskVerificationError("The response from Flathub seems fishy. Bailing out")


def run_flat_manager_client_process(context, args):
    flat_manager_client = context.config["flat_manager_client"]
    process = subprocess.Popen([flat_manager_client] + args, stdout=subprocess.PIPE)
    output, err = process.communicate()
    exit_code = process.wait()

    if exit_code != 0:
        raise RuntimeError("Command returned error: {}".format(exit_code))

    return output


def _check_file_exists(file_path):
    if not os.path.exists(file_path):
        raise TaskVerificationError(f"{file_path} file not found on disk!")


def _get_folder_path_for_file(file_path):
    return os.path.dirname(file_path)


def _check_tarball_is_valid(tarball_path):
    if not tarfile.is_tarfile(tarball_path):
        raise TaskVerificationError(f"{tarball_path} is not valid tarball!")


def _check_tarball_size(tarball_path):
    tar_size = os.path.getsize(tarball_path)
    tar_size_in_mb = tar_size // (1024 * 1024)

    if tar_size_in_mb > TAR_MAX_SIZE_IN_MB:
        raise TaskVerificationError(f"Tar {tarball_path} is too big. Max accepted size is {TAR_MAX_SIZE_IN_MB}")


def _check_tar_itself(tar_file_path):
    log.info("Check that flatpak tarball exists")
    _check_file_exists(tar_file_path)

    log.info("Check that flatpak tarball is a valid archive")
    _check_tarball_is_valid(tar_file_path)

    log.info("Check that flatpak tarball meets size requirements")
    _check_tarball_size(tar_file_path)

    log.info("Tarball looks good!")


def check_and_extract_tar_archive(context, tar_file_path):
    """Verify tar archives and extract them.

    This function is enriching the sanity checks that are already done as part
    of the tar module.

    * check if the tarball exists
    * check if flatpak tarball is a valid tarball
    * check if file size meets the requirements
    * TODO: check each file within the archive to ensure it's fine
    * TODO: check file in archive meet size requirements

    If any of these conditions is not met, then the function raises and exception
    and bails out without attempting to extract the files.

    Otherwise, files are extracted in the same folder as the tar archive, under
    the `repo` subfolder (inherited from the way we package flatpal in the
    `repackage` job).

    Raises:
        TaskVerificationError: whenever a tar archive breaks above assumption

    Returns:
        Location of the deflated flatpak tarball on local disk

    """
    _check_tar_itself(tar_file_path)

    flatpak_tar_basedir = _get_folder_path_for_file(tar_file_path)
    flatpak_deflated_dir = "repo"

    with tarfile.open(tar_file_path) as tar:
        topdir = tar.getnames()[0]
        if topdir != "repo":
            log.warning(f"{tar_file_path} does not have `repo` as topdir")
            flatpak_deflated_dir = topdir
        tar.extractall(path=flatpak_tar_basedir)

    # we remove the `tar.gz` as it's not longer needed
    os.remove(tar_file_path)
    log.debug(f"Deleted archive from {tar_file_path}")

    return os.path.join(flatpak_tar_basedir, flatpak_deflated_dir)


def sanitize_buildid(bytes_input):
    """Flathub API returns bytes to we're decoding that to unicode string"""
    return bytes_input.decode().strip()


def push(context, flatpak_file_path, channel):
    """ Publishes a flatpak into a given channel.
    """
    if not task.is_allowed_to_push_to_flathub(context.config, channel=channel):
        log.warning("Not allowed to push to Flathub. Skipping push...")
        # We don't raise an error because we still want green tasks on dev instances
        return

    token_args = ["--token-file", context.config["token_locations"][channel]]
    log.info(f"Grab a flatpak buildid from Flathub ...")
    publish_build_output = run_flat_manager_client_process(context, token_args + ["create", context.config["flathub_url"], channel])

    log.info(f"Sanitize the buildid received from Flathub ...")
    publish_build_output = sanitize_buildid(publish_build_output)
    log.info(f"Buildid output is {publish_build_output}")

    log.info(f"Validating the buildid ...")
    validate_publish_build_output(context, publish_build_output)

    log.info(f"Unpacking the tarball ...")
    deflated_dir = check_and_extract_tar_archive(context, flatpak_file_path)

    log.info(f"Pushing the flatpak to the associated {publish_build_output}")
    run_flat_manager_client_process(context, token_args + ["push", publish_build_output, deflated_dir])

    log.info(f"Commit-ing the flatpak to the associated {publish_build_output}")
    run_flat_manager_client_process(context, token_args + ["commit", "--wait", publish_build_output])

    log.info(f"Publishing the flatpak to the associated {publish_build_output}")
    run_flat_manager_client_process(context, token_args + ["publish", "--wait", publish_build_output])

    log.info(f"Cleaning up byt purging {publish_build_output}")
    run_flat_manager_client_process(context, token_args + ["purge", publish_build_output])
