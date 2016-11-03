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

import argparse
import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build

# Google play has currently 3 tracks. Rollout deploys
# to a limited percentage of users
TRACK_VALUES = ('production', 'beta', 'alpha', 'rollout')

PACKAGE_NAME_VALUES = {
    'org.mozilla.fennec_aurora': 'aurora',
    'org.mozilla.firefox_beta': 'beta',
    'org.mozilla.firefox': 'release'
}


def add_general_google_play_arguments(parser):
    parser.add_argument('--package-name', choices=PACKAGE_NAME_VALUES.keys(),
                        help='The Google play name of the app', required=True)

    parser.add_argument('--service-account', help='The service account email', required=True)
    parser.add_argument('--credentials', dest='google_play_credentials_file', type=argparse.FileType(mode='rb'),
                        default='key.p12', help='The p12 authentication file')

    parser.add_argument('--dry-run', action='store_true',
                        help='''Perform every operation of the transation, except committing. No data will be
stored on Google Play. Use this option if you want to test the script with the same data more than once.''')


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
