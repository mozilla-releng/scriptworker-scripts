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
import logging

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
# HACK: importing mock in production is useful for option `--do-not-contact-google-play`
from unittest.mock import MagicMock

from mozapkpublisher.common.exceptions import NoTransactionError, WrongArgumentGiven

# Google play has currently 4 tracks by default. Rollout deploys
# to a limited percentage of users
_DEFAULT_TRACK_VALUES = ['production', 'beta', 'alpha', 'rollout', 'internal']

# Google play allows the creation of custom release tracks for apps.
_ADDITIONAL_TRACK_VALUES = {
    'org.mozilla.focus': ['nightly'],
    'org.mozilla.klar': ['nightly']
}

logger = logging.getLogger(__name__)


def get_valid_track_values_for_package(package_name):
    return _DEFAULT_TRACK_VALUES + _ADDITIONAL_TRACK_VALUES.get(package_name, [])


def is_valid_track_value_for_package(track, package_name):
    return track in get_valid_track_values_for_package(package_name)


def add_general_google_play_arguments(parser):
    parser.add_argument('--service-account', help='The service account email', required=True)
    parser.add_argument('--credentials', dest='google_play_credentials_file', type=argparse.FileType(mode='rb'),
                        help='The p12 authentication file', required=True)

    parser.add_argument('--commit', action='store_true',
                        help='Commit changes onto Google Play. This action cannot be reverted.')
    parser.add_argument('--do-not-contact-google-play', action='store_false', dest='contact_google_play',
                        help='''Prevent any request to reach Google Play. Use this option if you want to run the script
without any valid credentials nor valid APKs. In fact, Google Play may error out at the first invalid piece of data sent.
--service-account and --credentials must still be provided (you can just fill them with random string and file).''')


def is_package_name_nightly(package_name):
    # Due to project Dawn, Nightly is now using the Aurora package name.
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=1357351
    return package_name == 'org.mozilla.fennec_aurora'


class EditService(object):
    def __init__(self, service_account, credentials_file_path, package_name, commit=False, contact_google_play=True):
        self._contact_google_play = contact_google_play
        if self._contact_google_play:
            general_service = connect(service_account, credentials_file_path)
            self._service = general_service.edits()
        else:
            self._service = _craft_google_play_service_mock()
            logger.warning('`--do-not-contact-google-play` option was given. Not a single request to Google Play will be made!')

        self._package_name = package_name
        self._commit = commit
        self.start_new_transaction()

    def start_new_transaction(self):
        result = self._service.insert(body={}, packageName=self._package_name).execute()
        self._edit_id = result['id']

    def transaction_required(method):
        def _transaction_required(*args, **kwargs):
            edit_service = args[0]
            if edit_service._edit_id is None:
                raise NoTransactionError(edit_service._package_name)

            return method(*args, **kwargs)
        return _transaction_required

    @transaction_required
    def commit_transaction(self):
        if self._commit:
            self._service.commit(editId=self._edit_id, packageName=self._package_name).execute()
            logger.info('Changes committed')
            logger.debug('edit_id "{}" for package "{}" has been committed'.format(self._edit_id, self._package_name))
        else:
            logger.warning('`commit` option was not given. Transaction not committed.')

        self._edit_id = None

    @transaction_required
    def upload_apk(self, apk_path):
        logger.info('Uploading "{}"'.format(apk_path))
        response = self._service.apks().upload(
            editId=self._edit_id,
            packageName=self._package_name,
            media_body=apk_path
        ).execute()
        logger.info('"{}" uploaded'.format(apk_path))
        logger.debug('Upload response: {}'.format(response))
        return response

    @transaction_required
    def update_track(self, track, version_codes, rollout_percentage=None):
        body = {u'versionCodes': version_codes}
        if rollout_percentage is not None:
            if rollout_percentage < 0 or rollout_percentage > 100:
                raise WrongArgumentGiven('rollout percentage must be between 0 and 100. Value given: {}'.format(rollout_percentage))

            body[u'userFraction'] = rollout_percentage / 100.0  # Ensure float in Python 2

        response = self._service.tracks().update(
            editId=self._edit_id, track=track, packageName=self._package_name, body=body
        ).execute()
        logger.info('Track "{}" updated with: {}'.format(track, body))
        logger.debug('Track update response: {}'.format(response))

    @transaction_required
    def update_listings(self, language, title, full_description, short_description):
        body = {
            'fullDescription': full_description,
            'shortDescription': short_description,
            'title': title,
        }
        response = self._service.listings().update(
            editId=self._edit_id, packageName=self._package_name, language=language, body=body
        ).execute()
        logger.info(u'Listing for language "{}" has been updated with: {}'.format(language, body))
        logger.debug(u'Listing response: {}'.format(response))

    @transaction_required
    def update_whats_new(self, language, apk_version_code, whats_new):
        response = self._service.apklistings().update(
            editId=self._edit_id, packageName=self._package_name, language=language,
            apkVersionCode=apk_version_code, body={'recentChanges': whats_new}
        ).execute()
        logger.info(u'What\'s new listing for ("{}", "{}") has been updated to: "{}"'.format(
            language, apk_version_code, whats_new
        ))
        logger.debug(u'Apk listing response: {}'.format(response))


def _craft_google_play_service_mock():
    edit_service_mock = MagicMock()

    edit_service_mock.insert = lambda *args, **kwargs: _ExecuteDummy({'id': 'fake-transaction-id'})
    edit_service_mock.commit = lambda *args, **kwargs: _ExecuteDummy(None)

    apks_mock = MagicMock()
    apks_mock.upload = lambda *args, **kwargs: _ExecuteDummy({'versionCode': 'fake-version-code'})
    edit_service_mock.apks = lambda *args, **kwargs: apks_mock

    update_mock = MagicMock()
    update_mock.update = lambda *args, **kwargs: _ExecuteDummy('fake-update-response')
    edit_service_mock.tracks = lambda *args, **kwargs: update_mock
    edit_service_mock.listings = lambda *args, **kwargs: update_mock
    edit_service_mock.apklistings = lambda *args, **kwargs: update_mock

    return edit_service_mock


class _ExecuteDummy():
    def __init__(self, return_value):
        self._return_value = return_value

    def execute(self):
        return self._return_value


def connect(service_account, credentials_file_path, api_version='v2'):
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

    service = build('androidpublisher', api_version, http=http, cache_discovery=False)

    return service
