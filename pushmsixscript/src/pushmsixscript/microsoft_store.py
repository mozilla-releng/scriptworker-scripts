import logging
import time

import requests
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


def push(config, msix_file_paths, channel):
    """Publishes a group of msix files onto a given channel.

    This function performs all the network actions to ensure `msix_file_paths` are published on
    `channel`. If `channel` is not whitelisted to contact the Microsoft Store, then it early
    returns (this allows staging tasks to not contact the Microsoft Store at all).

    Args:
        config (config): the scriptworker configuration.
        msix_file_paths (list of str): The full paths to the msix files to upload.
        channel (str): The Microsoft Store channel.
    """
    if not task.is_allowed_to_push_to_microsoft_store(config, channel=channel):
        log.warning("Not allowed to push to Microsoft Store. Skipping push...")
        # We don't raise an error because we still want green tasks on dev instances
        return

    access_token = _store_session(config)
    if access_token:
        _push_to_store(config, channel, msix_file_paths, access_token)
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


def _push_to_store(config, channel, msix_file_paths, access_token):
    headers = {"Authorization": f"Bearer {access_token}", "Content-type": "application/json", "User-Agent": "Python"}
    with requests.Session() as session:
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES))
        _remove_pending_submission(config, channel, session, headers)
        submission_request = _create_submission(config, channel, session, headers)
        submission_id = submission_request.get("id")
        _update_submission(config, channel, session, submission_request, headers, msix_file_paths)
        _commit_submission(config, channel, session, submission_id, headers)
        _wait_for_commit_completion(config, channel, session, submission_id, headers)


def _remove_pending_submission(config, channel, session, headers):
    # check for pending submission and delete it if anything is found
    application_id = config["application_ids"][channel]
    url = _store_url(config, f"{application_id}")
    response = session.get(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
    _log_response(response)
    response.raise_for_status()
    response_json = response.json()
    if "pendingApplicationSubmission" in response_json:
        submission_to_remove = response_json["pendingApplicationSubmission"]["id"]
        url = _store_url(config, f"{application_id}/submissions/{submission_to_remove}")
        session.delete(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
        _log_response(response)
        response.raise_for_status()


def _create_submission(config, channel, session, headers):
    # create a new in-progress submission, which is a copy of the last published submission
    application_id = config["application_ids"][channel]
    url = _store_url(config, f"{application_id}/submissions")
    response = session.post(url, headers=headers, timeout=int(config["request_timeout_seconds"]))
    _log_response(response)
    response.raise_for_status()
    return response.json()


def _update_submission(config, channel, session, submission_request, headers, file_paths):
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
    # The Store expects all-lower-case 'true' and 'false' in the submission request.
    submission_request = str(submission_request)
    submission_request = submission_request.replace("True", "true").replace("False", "false")
    url = _store_url(config, f"{application_id}/submissions/{submission_id}")
    response = session.put(url, submission_request, headers=headers)
    _log_response(response)
    response.raise_for_status()
    for file_path in file_paths:
        with open(file_path, "rb") as f:
            upload_headers = {"x-ms-blob-type": "BlockBlob"}
            response = requests.put(upload_url, f, headers=upload_headers, timeout=int(config["request_timeout_seconds"]))
            response.raise_for_status()
            _log_response(response)
            # no response body expected


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
