import logging
import subprocess

from scriptworker.exceptions import TaskVerificationError

from pushflatpakscript import task

log = logging.getLogger(__name__)

FLATAHUB_API_RESPONSE_PREFIX = "{flathub_url}api/v1/build/"


def validate_publish_build_output(context, content):
    prefix = FLATAHUB_API_RESPONSE_PREFIX.format(flathub_url=context.config["flathub_url"])
    if not content.startswith(prefix):
        raise TaskVerificationError("The response from Flathub seems fishy. Bailing out")


def run_flat_manager_client_process(context, command, *args):
    extra_args = [arg for arg in args]
    flat_manager_client = context.config["flat_manager_client"]
    process = subprocess.Popen([flat_manager_client, command] + extra_args, stdout=subprocess.PIPE)
    output, err = process.communicate()
    exit_code = process.wait()

    if exit_code != 0:
        raise RuntimeError("Command returned error: {}".format(exit_code))

    return output


def push(context, flatpak_file_path, channel):
    """ Publishes a flatpak into a given channel.
    """
    if not task.is_allowed_to_push_to_flathub(context.config, channel=channel):
        log.warning("Not allowed to push to Flathub. Skipping push...")
        # We don't raise an error because we still want green tasks on dev instances
        return

    publish_build_output = run_flat_manager_client_process(context, "create", context.config["flathub_url"], channel)
    validate_publish_build_output(publish_build_output)

    # TODO: implement zip logic to unarchive the flatpak_file_path

    # XXX: `repo` is hardcodede as it's always baked under that form in the flatpak
    publish_build_output = run_flat_manager_client_process(context, "push", publish_build_output, "repo")

    publish_build_output = run_flat_manager_client_process(context, "commit", "--wait", publish_build_output)

    publish_build_output = run_flat_manager_client_process(context, "publish", "--wait", publish_build_output)

    publish_build_output = run_flat_manager_client_process(context, "purge", publish_build_output)
