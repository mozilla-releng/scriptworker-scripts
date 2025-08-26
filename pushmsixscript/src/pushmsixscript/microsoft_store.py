import json
import logging
import os
import tempfile
import time
import traceback
import zipfile
from copy import copy

import requests
from azure.storage.blob import BlobClient

from pushmsixscript import task
from scriptworker_client.exceptions import TaskError, TimeoutError

log = logging.getLogger(__name__)

# When committing a new submission, poll for completion, with
# this many attempts, waiting this long between attempts.
COMMIT_POLL_MAX_ATTEMPTS = 40
COMMIT_POLL_WAIT_SECONDS = 30
# Max requests retries
MAX_RETRIES = 5
DEFAULT_LISTINGS = {
    "en-us": {
        "baseListing": {
            "copyrightAndTrademarkInfo": "",
            "keywords": [],
            "licenseTerms": "",
            "privacyPolicy": "",
            "supportContact": "",
            "websiteUrl": "",
            "description": "Description",
            "features": [],
            "releaseNotes": "",
            "images": [],
            "recommendedHardware": [],
            "title": "Firefox Nightly",
        }
    }
}
DEFAULT_ALLOW_TARGET = {"Desktop": True, "Mobile": False, "Holographic": False, "Xbox": False}


def push(config, msix_file_paths, channel, publish_mode=None):
    """Publishes a group of msix files onto a given channel.

    This function performs all the network actions to ensure `msix_file_paths` are published on
    `channel`. If `channel` is not whitelisted to contact the Microsoft Store, then it early
    returns (this allows staging tasks to not contact the Microsoft Store at all).

    Args:
        config (config): the scriptworker configuration.
        msix_file_paths (list of str): The full paths to the msix files to upload.
        channel (str): The Microsoft Store channel name: "release", "beta", etc.
        publish_mode (str): A Store "targetPublishMode" value like "Immediate" or
            "Manual", or None to use the existing targetPublishMode.
    """
    if not task.is_allowed_to_push_to_microsoft_store(config, channel=channel):
        log.warning("Not allowed to push to Microsoft Store. Skipping push...")
        # We don't raise an error because we still want green tasks on dev instances
        return

    access_token = _store_session(config)
    if access_token:
        _push_to_store(config, channel, msix_file_paths, publish_mode, access_token)
    else:
        raise TaskError("unable to push: missing access token")


def _store_url(config, tail):
    return config["store_url"] + tail


def _log_response(response):
    try:
        log.info(f"response code: {response.status_code}")
        if hasattr(response, "text"):
            max_len = 1000
            body = (response.text[:max_len] + "...") if len(response.text) > max_len else response.text
            log.info(f"response body: {body}")
    except Exception:
        log.error("unable to log response")
        traceback.print_exc()


def _store_session(config):
    tenant_id = config["tenant_id"]
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    login_url = config["login_url"]
    token_resource = config["token_resource"]
    url = f"{login_url}/{tenant_id}/oauth2/token"
    body = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}&resource={token_resource}"
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
    with requests.Session() as session:
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES))
        response = session.post(url, body, headers=headers, timeout=int(config["request_timeout_seconds"]))
        response.raise_for_status()
        return response.json().get("access_token")


def _push_to_store(config, channel, msix_file_paths, publish_mode, access_token):
    headers = {"Authorization": f"Bearer {access_token}", "Content-type": "application/json", "User-Agent": "Python"}
    with requests.Session() as session:
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES))
        log.info(">> checking for pending submissions...")
        _check_for_pending_submission(config, channel, session, headers)
        log.info(">> creating a new submission...")
        (submission_request, encoding) = _create_submission(config, channel, session, headers)
        submission_id = submission_request.get("id")
        log.info(">> updating the submission...")
        _update_submission(config, channel, session, submission_request, headers, msix_file_paths, publish_mode, encoding)
        # Commit the submission.
        # We previously tried skipping the commit on the Release channel, to give
        # Release Management a chance to edit the submission prior to certification;
        # this strategy did not work: we found that, inexplicably, the changes to
        # the package (the msix upload) were lost.
        log.info(">> committing the submission...")
        _commit_submission(config, channel, session, submission_id, headers)
        log.info(">> waiting for completion...")
        _wait_for_commit_completion(config, channel, session, submission_id, headers)

        log.info(">> push complete!")


def _check_for_pending_submission(config, channel, session, headers):
    # Check for pending submission and abort if found. It is also possible
    # to delete the pending submission and continue, but that risks removing
    # submission data (like privacy policy, screenshots) that may have been
    # recently updated in the pending submission.
    application_id = config["application_ids"][channel]
    url = _store_url(config, f"{application_id}")
    response = session.get(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
    _log_response(response)
    response.raise_for_status()
    response_json = response.json()
    if "pendingApplicationSubmission" in response_json:
        log.error(
            "There is a pending submission for this application on "
            "the Microsoft Store. Wait for the pending submission to "
            "complete, or delete the pending submission. Then retry this task."
        )
        raise TaskError("push to Store aborted: pending submission found")


def _create_submission(config, channel, session, headers):
    # create a new in-progress submission, which is a copy of the last published submission
    application_id = config["application_ids"][channel]
    url = _store_url(config, f"{application_id}/submissions")
    response = session.post(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
    _log_response(response)
    response.raise_for_status()
    log.info(f"submission data response encoding: {response.encoding}")
    return (response.json(), response.encoding)


def _update_submission(config, channel, session, submission_request, headers, file_paths, publish_mode, encoding):
    # update the in-progress submission, including uploading the new msix files
    application_id = config["application_ids"][channel]
    submission_id = submission_request.get("id")
    submission_request, upload_file_names = _craft_new_submission_request_and_upload_file_names(config, channel, submission_request, file_paths, publish_mode)
    upload_url = submission_request.get("fileUploadUrl")
    upload_url = upload_url.replace("+", "%2B")

    url = _store_url(config, f"{application_id}/submissions/{submission_id}")
    response = session.put(url, _encode_submission_request(submission_request, encoding), headers=headers)
    _log_response(response)
    response.raise_for_status()
    # Wrap all the msix files in a zip file and upload the zip
    with tempfile.TemporaryDirectory() as work_dir:
        zip_file_name = os.path.join(work_dir, "pushmsix.zip")
        with zipfile.ZipFile(zip_file_name, "w") as zf:
            for file_path in file_paths:
                zf.write(file_path, arcname=upload_file_names[file_path])
        # Note that simple HTTP uploads fail for large files (like ours!), so
        # using the BlobClient is required.
        blob_client = BlobClient.from_blob_url(upload_url)
        with open(zip_file_name, "rb") as f:
            d = blob_client.upload_blob(f, blob_type="BlockBlob", logging_enable=False)
            log.debug(f"upload response: {d}")


def _craft_new_submission_request_and_upload_file_names(config, channel, submission_request, file_paths, publish_mode):
    submission_request = copy(submission_request)
    # submission_request is a copy of the submission info used for the
    # previous successful submission; normally, no content changes are
    # needed for this new submission. However, when creating the first
    # submission for a Store application (or if the previous submission
    # info is lost somehow?), a few defaults may avoid errors. If having
    # trouble here, consider sorting it out in the Partner Center.
    if submission_request.get("applicationCategory") == "NotSet":
        submission_request["applicationCategory"] = "Productivity"
    if not submission_request.get("listings"):
        submission_request["listings"] = DEFAULT_LISTINGS
    if not submission_request.get("allowTargetFutureDeviceFamilies"):
        submission_request["allowTargetFutureDeviceFamilies"] = DEFAULT_ALLOW_TARGET
    if publish_mode:
        submission_request["targetPublishMode"] = publish_mode
        log.info(f"using targetPublishMode override: {publish_mode}")
    else:
        log.info("using existing targetPublishMode (task publishMode not specified)")
    for package in submission_request.get("applicationPackages", []):
        package["fileStatus"] = "PendingDelete"
    # "Upload file names" are file names specified in the submission request.
    # The zip file's members must match the upload file names.
    # Upload file names appear on the Partner Center website but are not
    # available to the public (do not appear in the Store). The Partner Center
    # examines the uploaded files and displays the architecture (like "x86")
    # and msix application version number alongside each upload file name.
    # The basic "target.store.X.msix" name format is chosen to reflect the
    # file names used for the treeherder artifacts; {index} is added to make
    # each upload file name unique within the zip file; {datestamp} is added
    # as a simple sanity check but is otherwise superfluous.
    # Note that using the exact same upload file names for a subsequent
    # submission is absolutely fine.
    upload_file_names = {}
    datestamp = time.strftime("%y%m%d")
    index = 1
    for file_path in file_paths:
        upload_file_names[file_path] = f"target.store.{datestamp}.{index}.msix"
        index += 1
    for file_path in file_paths:
        package = {
            "fileName": upload_file_names[file_path],
            "fileStatus": "PendingUpload",
            "minimumDirectXVersion": submission_request["applicationPackages"][0]["minimumDirectXVersion"],
            "minimumSystemRam": submission_request["applicationPackages"][0]["minimumSystemRam"],
        }
        submission_request["applicationPackages"].append(package)
    # Bug 1776696 / bug 1779435: Once commited, the submission will automatically go
    # to certification. The submission cannot be edited while in certification; the
    # Partner Center user must cancel certification, edit the submission, and then
    # re-submit. Specification of a common rollout % may reduce the need for manual
    # intervention.
    if channel == "release":
        if "release_rollout_percentage" in config:
            delivery_options = submission_request.setdefault("packageDeliveryOptions", {})
            package_rollout = delivery_options.setdefault("packageRollout", {})
            package_rollout["isPackageRollout"] = True
            package_rollout["packageRolloutPercentage"] = config["release_rollout_percentage"]

    return submission_request, upload_file_names


def _encode_submission_request(submission_request, encoding):
    submission_json_string = json.dumps(submission_request)
    return submission_json_string.encode(encoding)


def _commit_submission(config, channel, session, submission_id, headers):
    # finalize submission
    application_id = config["application_ids"][channel]
    url = _store_url(config, f"{application_id}/submissions/{submission_id}/commit")
    response = session.post(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
    _log_response(response)
    response.raise_for_status()
    return response.json()


def _get_submission_status(config, channel, session, submission_id, headers):
    application_id = config["application_ids"][channel]
    url = _store_url(config, f"{application_id}/submissions/{submission_id}/status")
    response = session.get(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
    _log_response(response)
    response.raise_for_status()
    return response.json()


def _wait_for_commit_completion(config, channel, session, submission_id, headers):
    # pull submission status until commit process is completed
    response_json = _get_submission_status(config, channel, session, submission_id, headers)
    log.info(response_json.get("status"))
    attempts = 1
    # TODO: Confirm what the status is for a complete submission!
    while response_json.get("status") not in ("PreProcessing", "CommitFailed"):
        if attempts > COMMIT_POLL_MAX_ATTEMPTS:
            log.error(
                "This task reached the max polling attempts for a submission and may "
                "have left a pending submission in the Store. "
                "It may be possible to edit it and submit it manually from the Partner "
                "Center. Otherwise, try deleting the pending submission and retry this "
                "task."
            )
            raise TimeoutError("push to Store failed on polling commits")
        attempts += 1
        time.sleep(COMMIT_POLL_WAIT_SECONDS)
        response_json = _get_submission_status(config, channel, session, submission_id, headers)
        log.info(response_json.get("status"))
    if "Failed" in response_json.get("status", ""):
        log.error(
            "This task failed and may have left a pending submission in the Store. "
            "It may be possible to edit it and submit it manually from the Partner "
            "Center. Otherwise, try deleting the pending submission and retry this "
            "task."
        )
        raise TaskError("push to Store failed on commit")
    return True
