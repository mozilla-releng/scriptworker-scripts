import json
import logging
import http.client, requests, time

from pushmsixscript import task

log = logging.getLogger(__name__)


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
    # _push_to_store(msix_file_path, access_token)

    # _release_if_needed(store, channel, msix_file_path)


def _store_session(tenantId, clientId, clientSecret):

    tokenResource = "https://manage.devcenter.microsoft.com"

    tokenRequestBody = "grant_type=client_credentials&client_id={0}&client_secret={1}&resource={2}".format(clientId, clientSecret, tokenResource)
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
    tokenConnection = http.client.HTTPSConnection("login.microsoftonline.com")
    tokenConnection.request("POST", "/{0}/oauth2/token".format(tenantId), tokenRequestBody, headers=headers)

    tokenResponse = tokenConnection.getresponse()
    log.info(tokenResponse.status)
    tokenJson = json.loads(tokenResponse.read().decode())
    log.info(tokenJson["access_token"])

    tokenConnection.close()

    return tokenJson["access_token"]


def _push_to_store(msix_file_path, accessToken):
    applicationId = ""  # Your application ID
    appSubmissionRequestJson = "";  # Your submission request JSON

    headers = {"Authorization": "Bearer " + accessToken,
               "Content-type": "application/json",
               "User-Agent": "Python"}

    conn = http.client.HTTPSConnection("manage.devcenter.microsoft.com")

    _remove_pending_submission(conn, applicationId, headers)
    (submissionId, fileUploadUrl) = _create_submission(conn, applicationId, headers)
    # XXX example says "zipFilePath" -- is msix okay?
    _update_submission(conn, applicationId, submissionId, headers, appSubmissionRequestJson, msix_file_path, fileUploadUrl)
    _commit_submission(conn, applicationId, submissionId, headers)
    _wait_for_commit_completion(conn, applicationId, submissionId, headers)

    conn.close()


def _wait_for_commit_completion(conn, applicationId, submissionId, headers):
    # Pull submission status until commit process is completed
    responseJson = _get_submission_status(conn, applicationId, submissionId, headers)
    # XXX timeout / max retries?
    while responseJson["status"] == "CommitStarted":
        time.sleep(60)
        responseJson = _get_submission_status(conn, applicationId, submissionId, headers)
        log.info(responseJson["status"])


def _create_submission(conn, applicationId, headers):
    req = "/v1.0/my/applications/{0}/submissions".format(applicationId)
    conn.request("POST", req, "", headers)
    response = conn.getresponse()
    log.info(response.status)
    log.info(response.headers["MS-CorrelationId"])  # Log correlation ID
    responseJson = json.loads(response.read().decode())
    submissionId = responseJson["id"]
    fileUploadUrl = responseJson["fileUploadUrl"]
    log.info(submissionId)
    log.info(fileUploadUrl)
    return (submissionId, fileUploadUrl)


def _remove_pending_submission(conn, applicationId, headers):
    # Get application
    conn.request("GET", "/v1.0/my/applications/{0}".format(applicationId), "", headers)
    response = conn.getresponse()
    log.info(response.status)
    log.info(response.headers["MS-CorrelationId"])  # Log correlation ID

    # Delete existing in-progress submission
    responseJson = json.loads(response.read().decode())
    if "pendingApplicationSubmission" in responseJson :
        submissionToRemove = responseJson["pendingApplicationSubmission"]["id"]
        req = "/v1.0/my/applications/{0}/submissions/{1}".format(applicationId, submissionToRemove)
        conn.request("DELETE", req, "", headers)
        response = conn.getresponse()
        log.info(response.status)
        log.info(response.headers["MS-CorrelationId"])  # Log correlation ID
        response.read()


def _update_submission(conn, applicationId, submissionId, headers, appSubmissionRequestJson, zipFilePath, fileUploadUrl):
    req = "/v1.0/my/applications/{0}/submissions/{1}".format(applicationId, submissionId)
    conn.request("PUT", req, appSubmissionRequestJson, headers)
    response = conn.getresponse()
    log.info(response.status)
    log.info(response.headers["MS-CorrelationId"])  # Log correlation ID
    response.read()
    # Upload images and packages in a zip file. Note that large file might need to be handled differently
    with open(zipFilePath, 'rb') as f:
        response = requests.put(fileUploadUrl.replace("+", "%2B"), f, headers={"x-ms-blob-type": "BlockBlob"})
        log.info(response.status_code)


def _commit_submission(conn, applicationId, submissionId, headers):
    req = "/v1.0/my/applications/{0}/submissions/{1}/commit".format(applicationId, submissionId)
    conn.request("POST", req, "", headers)
    response = conn.getresponse()
    log.info(response.status)
    log.info(response.headers["MS-CorrelationId"])  # Log correlation ID
    log.info(response.read())
    # XXX verify response?


def _get_submission_status(conn, applicationId, submissionId, headers):
    req = "/v1.0/my/applications/{0}/submissions/{1}/status".format(applicationId, submissionId)
    conn.request("GET", req, "", headers)
    response = conn.getresponse()
    return json.loads(response.read().decode())
