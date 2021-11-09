import logging
import time

import requests

from pushmsixscript import task

log = logging.getLogger(__name__)

# When committing a new submission, poll for completion, with
# this many attempts, waiting this long between attempts.
COMMIT_POLL_MAX_ATTEMPTS = 10
COMMIT_POLL_WAIT_SECONDS = 30

# XXX channels
# XXX request timeouts
# XXX request retries
# XXX what is our application_id, might it change? should that be in config?
# XXX what goes in the submission_json?
# XXX is msix file okay, or does it need to be a zip?


def push(context, msix_file_path, channel):
    """Publishes a msix onto a given channel.

    This function performs all the network actions to ensure `msix_file_path` is published on
    `channel`. If `channel` is not whitelisted to contact the Microsoft Store, then it just early
    returns (this allows staging tasks to not contact the Microsoft Store instance at all). If allowed,
    this function first connects to the Microsoft Store, then uploads the msix onto it. No matter
    whether the msix has already been uploaded, it proceeds to the next step. If the msix is
    already released, then there's nothing to do and the function simply returns. Otherwise, the
    msix must have a higher version (or build) number to overwrite the existing one. If the version
    number happens to be lower or the same one (while still being a different msix), then the
    function bails out.

    Args:
        context (scriptworker.context.Context): the scriptworker context.
        msix_file_path (str): The full path to the msix file
        channel (str): The Snap Store channel.
    """
    if not task.is_allowed_to_push_to_microsoft_store(context.config, channel=channel):
        log.warning("Not allowed to push to Microsoft Store. Skipping push...")
        # We don't raise an error because we still want green tasks on dev instances
        return

    access_token = _store_session()
    if access_token:
        log.info(access_token)
        # application_id = ""  # Your application ID
        # app_submission_request = ""  # Your submission request JSON
        # _push_to_store(msix_file_path, access_token, application_id, app_submission_request)
        # _release_if_needed(store, channel, msix_file_path)


def _store_url(tail):
    return "https://manage.devcenter.microsoft.com/v1.0/my/applications/" + tail


def _log_response(response):
    log.info(f"response code: {response.status_code}")
    log.info(f"response headers: {response.headers}")
    log.info(f"response body: {response.text}")


def _store_session(tenant_id, client_id, client_secret):
    token_resource = "https://manage.devcenter.microsoft.com"
    url = "https://login.microsoftonline.com/{0}/oauth2/token".format(tenant_id)
    body = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}&resource={token_resource}"
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
    response = requests.post(url, body, headers=headers)
    _log_response(response)
    response.raise_for_status()
    return response.json().get("access_token")


def _push_to_store(msix_file_path, access_token, application_id, app_submission_request):
    headers = {"Authorization": "Bearer " + access_token, "Content-type": "application/json", "User-Agent": "Python"}
    with requests.Session() as session:
        _remove_pending_submission(session, application_id, headers)
        (submission_id, upload_url) = _create_submission(session, application_id, headers)
        _update_submission(session, application_id, submission_id, headers, app_submission_request, msix_file_path, upload_url)
        _commit_submission(session, application_id, submission_id, headers)
        _wait_for_commit_completion(session, application_id, submission_id, headers)


def _remove_pending_submission(session, application_id, headers):
    # Get application
    url = _store_url(f"{application_id}")
    response = session.get(url, headers=headers)
    _log_response(response)
    response.raise_for_status()

    # Delete existing in-progress submission
    response_json = response.json()
    if "pendingApplicationSubmission" in response_json:
        submission_to_remove = response_json["pendingApplicationSubmission"]["id"]
        url = _store_url(f"{application_id}/submissions/{submission_to_remove}")
        session.delete(url, headers=headers)
        _log_response(response)
        response.raise_for_status()


def _create_submission(session, application_id, headers):
    url = _store_url(f"{application_id}/submissions")
    response = session.post(url, headers=headers)
    _log_response(response)
    response.raise_for_status()
    response_json = response.json()
    submission_id = response_json.get("id")
    upload_url = response_json.get("upload_url")
    return (submission_id, upload_url)


def _update_submission(session, application_id, submission_id, headers, app_submission_request, file_path, upload_url):
    url = _store_url(f"{application_id}/submissions/{submission_id}")
    response = session.put(url, app_submission_request, headers=headers)
    _log_response(response)
    response.raise_for_status()
    # Upload images and packages in a zip file. Note that large file might need to be handled differently
    with open(file_path, "rb") as f:
        response = requests.put(upload_url.replace("+", "%2B"), f, headers={"x-ms-blob-type": "BlockBlob"})
        response.raise_for_status()
        _log_response(response)


def _commit_submission(session, application_id, submission_id, headers):
    url = _store_url(f"{application_id}/submissions/{submission_id}/commit")
    response = session.post(url, headers=headers)
    _log_response(response)
    response.raise_for_status()
    # XXX verify response body?


def _get_submission_status(session, application_id, submission_id, headers):
    url = _store_url(f"{application_id}/submissions/{submission_id}/status")
    response = session.get(url, headers=headers)
    _log_response(response)
    response.raise_for_status()
    return response.json()


def _wait_for_commit_completion(session, application_id, submission_id, headers):
    # Pull submission status until commit process is completed
    response_json = _get_submission_status(session, application_id, submission_id, headers)
    attempts = 1
    while response_json.get("status") == "CommitStarted":
        if attempts > COMMIT_POLL_MAX_ATTEMPTS:
            return False
        attempts += 1
        time.sleep(COMMIT_POLL_WAIT_SECONDS)
        response_json = _get_submission_status(session, application_id, submission_id, headers)
        log.info(response_json.get("status"))
    return True
