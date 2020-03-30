## This should live in balrogclient in the balrog repo, placed here to facilitate easy testing

import requests

from balrogclient.api import _get_auth0_token, BearerAuth


def get_balrog_api(auth0_secrets, session=None):
    if not session:
        session = requests.Session()

    access_token = _get_auth0_token(auth0_secrets, session=session)
    session.auth = BearerAuth(access_token)
    return session
