""" googleplay.py

    The way to get the API access is to
      1) login in in the Google play admin
      2) Settings
      3) API Access
      4) go in the Google Developers Console
      5) Create "New client ID"
         or download the p12 key (it should remain
         super private)
      6) Move the file in this directory with the name
         'key.p12' or use the --credentials option
"""

import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build


def connect(service_account, credentials_file_path):
    """ Connect to the google play interface
    """

    # Create an httplib2.Http object to handle our HTTP requests an
    # authorize it with the Credentials. Note that the first parameter,
    # service_account_name, is the Email address created for the Service
    # account. It must be the email address associated with the key that
    # was created.
    scope = 'https://www.googleapis.com/auth/androidpublisher'
    credentials = ServiceAccountCredentials.from_p12_keyfile(service_account, credentials_file_path, scopes=scope)
    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('androidpublisher', 'v2', http=http)

    return service
