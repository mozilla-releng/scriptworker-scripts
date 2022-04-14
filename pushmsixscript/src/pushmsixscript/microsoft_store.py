import logging
import os
import tempfile
import time
import zipfile

import requests
from azure.storage.blob import BlobClient
from scriptworker_client.exceptions import TaskVerificationError

from pushmsixscript import task

log = logging.getLogger(__name__)

# When committing a new submission, poll for completion, with
# this many attempts, waiting this long between attempts.
COMMIT_POLL_MAX_ATTEMPTS = 10
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
        raise TaskVerificationError("unable to push: missing access token")


def _store_url(config, tail):
    return config["store_url"] + tail


def _log_response(response):
    log.info(f"response code: {response.status_code}")
    # log.info(f"response headers: {response.headers}")
    log.info(f"response body: {response.text}")


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
        _check_for_pending_submission(config, channel, session, headers)
        submission_request = _create_submission(config, channel, session, headers)
        submission_id = submission_request.get("id")
        _update_submission(config, channel, session, submission_request, headers, msix_file_paths, publish_mode)
        _commit_submission(config, channel, session, submission_id, headers)
        _wait_for_commit_completion(config, channel, session, submission_id, headers)


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
        raise TaskVerificationError("push to Store aborted: pending submission found")


def _create_submission(config, channel, session, headers):
    # create a new in-progress submission, which is a copy of the last published submission
    application_id = config["application_ids"][channel]
    url = _store_url(config, f"{application_id}/submissions")
    response = session.post(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
    _log_response(response)
    response.raise_for_status()
    return response.json()


def _update_submission(config, channel, session, submission_request, headers, file_paths, publish_mode):
    # update the in-progress submission, including uploading the new msix file
    application_id = config["application_ids"][channel]
    submission_id = submission_request.get("id")
    upload_url = submission_request.get("fileUploadUrl")
    upload_url = upload_url.replace("+", "%2B")
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
    for package in submission_request.get("applicationPackages"):
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

    # The Store expects all-lower-case 'true' and 'false' in the submission request.
    submission_request = str(submission_request)
    submission_request = submission_request.replace("True", "true").replace("False", "false")
    url = _store_url(config, f"{application_id}/submissions/{submission_id}")
    response = session.put(url, submission_request, headers=headers)
    _log_response(response)
    response.raise_for_status()
    with tempfile.TemporaryDirectory() as work_dir:
        zip_file_name = os.path.join(work_dir, "pushmsix.zip")
        with zipfile.ZipFile(zip_file_name, "w") as zf:
            for file_path in file_paths:
                zf.write(file_path, arcname=upload_file_names[file_path])
        blob_client = BlobClient.from_blob_url(upload_url)
        with open(zip_file_name, "rb") as f:
            blob_client.upload_blob(f, blob_type="BlockBlob", logging_enable=False)


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
    attempts = 1
    while response_json.get("status") == "CommitStarted":
        if attempts > COMMIT_POLL_MAX_ATTEMPTS:
            return False
        attempts += 1
        time.sleep(COMMIT_POLL_WAIT_SECONDS)
        response_json = _get_submission_status(config, channel, session, submission_id, headers)
        log.info(response_json.get("status"))
    return True
