# This should live in balrogclient in the balrog repo, placed here to facilitate easy testing

import json
import logging
import time

import requests
from balrogclient.api import BearerAuth, _get_auth0_token

log = logging.getLogger(__name__)


def get_balrog_api(auth0_secrets, session=None):
    if not session:
        session = requests.Session()

    access_token = _get_auth0_token(auth0_secrets, session=session)
    session.auth = BearerAuth(access_token)
    return session


def do_balrog_req(url, data=None, method="get", auth0_secrets=None):
    requests_api = get_balrog_api(auth0_secrets=auth0_secrets)
    log.debug("Balrog request to %s via %s", url, method.upper())
    log.debug("Data sent: %s", json.dumps(data))
    before = time.time()
    resp = requests_api.request(url=url, method=method, json=data)
    try:
        resp.raise_for_status()
        if resp.content:
            recieved_data = resp.json()
            log.info("Data recieved: %s", recieved_data)
            return recieved_data
        else:
            return
    except requests.HTTPError as excp:
        log.error("Caught HTTPError: %s", excp.response.content)
        raise
    finally:
        stats = {"timestamp": time.time(), "method": method.upper(), "url": url, "status_code": resp.status_code, "elapsed_secs": time.time() - before}
        log.debug("REQUEST STATS: %s", json.dumps(stats))
    return
