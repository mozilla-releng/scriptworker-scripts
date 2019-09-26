from contextlib import contextmanager

import httplib2
import json
import logging

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.errors import HttpError
# HACK: importing mock in production is useful for option `--do-not-contact-google-play`
from unittest.mock import MagicMock

from mozapkpublisher.common.exceptions import WrongArgumentGiven
import requests

logger = logging.getLogger(__name__)


BASE_AMAZON_URL = 'https://developer.amazon.com/api/appstore/v1'
AMAZON_RECENT_CHANGES = {
    'en-US': 'Bug fixes and technical improvements.',
    'de-DE': 'Fehlerkorrekturen und Technische Verbesserungen.',
    'fr-FR': 'Correction de bugs et amélioration des techniques.',
}


def add_general_google_play_arguments(parser):
    parser.add_argument('--service-account', help='The service account email', required=True)
    parser.add_argument('--credentials', dest='google_play_credentials_filename',
                        help='The p12 authentication file', required=True)

    parser.add_argument('--commit', action='store_true',
                        help='Commit changes onto Google Play. This action cannot be reverted.')
    parser.add_argument('--do-not-contact-google-play', action='store_false', dest='contact_google_play',
                        help='''Prevent any request to reach Google Play. Use this option if you want to run the script
without any valid credentials nor valid APKs. In fact, Google Play may error out at the first invalid piece of data sent.
--service-account and --credentials must still be provided (you can just fill them with random string and file).''')


class _ExecuteDummy:
    def __init__(self, return_value):
        self._return_value = return_value

    def execute(self):
        return self._return_value


def http(expected_status, method, url, **kwargs):
    response = requests.request(
        method=method,
        url=url,
        **kwargs,
    )
    if response.status_code != expected_status:
        raise RuntimeError(f'Expected "{method}" to "{url}" to have status code '
                           f'"{expected_status}", but received "{response.status_code}" '
                           f'("{response.text}") instead')
    return response


class AmazonAuth(requests.auth.AuthBase):
    def __init__(self, access_token):
        self._access_token = access_token

    def __call__(self, request: requests.Request):
        request.headers['Authorization'] = f'Bearer {self._access_token}'
        return request


class AmazonStoreEdit:
    def __init__(self, auth, edit_it, package_name):
        self._auth = auth
        self._edit_id = edit_it
        self._package_name = package_name

    def _http(self, expected_status, method, endpoint, **kwargs):
        url = f'{BASE_AMAZON_URL}/applications/{self._package_name}/edits/{self._edit_id}' + endpoint

        return http(expected_status, method, url, auth=self._auth, **kwargs)

    def update_app(self, extracted_apks):
        body = self._http(200, 'get', '/apks').json()
        existing_apk_ids = [apk['id'] for apk in body]

        for apk_id in existing_apk_ids:
            response = self._http(200, 'get', f'/apks/{apk_id}')
            etag = response.headers['ETag']
            self._http(204, 'delete', f'/apks/{apk_id}', headers={'If-Match': etag})

        # TODO: simplify update_app(...) so it just takes [apks], rather than [(apk, _unused)]
        for apk, _ in extracted_apks:
            self._http(200, 'post', '/apks/upload', data=apk,
                       headers={'Content-Type': 'application/octet-stream'})

        response = self._http(200, 'get', '/listings')
        languages = response.json()['listings'].keys()
        for locale in languages:
            response = self._http(200, 'get', f'/listings/{locale}')
            etag = response.headers['ETag']
            listing = response.json()
            listing['recentChanges'] = AMAZON_RECENT_CHANGES.get(locale, '✔')

            self._http(200, 'put', f'/listings/{locale}', headers={'If-Match': etag}, json=listing)

    def validate(self):
        self._http(200, 'post', '/validate')

    def cancel(self):
        response = self._http(200, 'get', '')
        etag = response.headers['ETag']

        self._http(204, 'delete', '', headers={'If-Match': etag})

    @staticmethod
    @contextmanager
    def transaction(client_id, client_secret, package_name, *, contact_server, dry_run):
        if contact_server:
            response = http(200, 'post', 'https://api.amazon.com/auth/o2/token', data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'client_credentials',
                'scope': 'appstore::apps:readwrite',
            })
            auth = AmazonAuth(response.json()['access_token'])

            response = http(200, 'get', f'{BASE_AMAZON_URL}/applications/{package_name}/edits', auth=auth)
            if response.text != '{}':
                # Only one "upcoming version" is allowed at a time. We could automatically delete
                # the existing one and create a new one, but that could cause loss of data (e.g.:
                # if someone is manually creating a release)
                raise RuntimeError(f'The app "{package_name}" already has an "upcoming '
                                   f'version". Please submit or delete that upcoming '
                                   f'version from the Amazon Developer Console.')

            response = http(200, 'post', f'{BASE_AMAZON_URL}/applications/{package_name}/edits', auth=auth)
            edit_id = response.json()['id']
            edit = AmazonStoreEdit(auth, edit_id, package_name)
        else:
            logger.warning('Not a single request to Amazon will be made, since `contact_server` '
                           'was set to `False`')
            edit = MockAmazonStoreEdit()

        try:
            yield edit
            edit.validate()
            if dry_run:
                logger.warning('`try_run` was `True`. Cancelling the edit...')
                edit.cancel()
        except BaseException:
            logger.warning('An error was encountered, cancelling the edit...')
            edit.cancel()
            raise


class MockAmazonStoreEdit:
    def update_app(self, apks):
        pass

    def validate(self):
        pass

    def cancel(self):
        pass


class GooglePlayEdit:
    """Represents an "edit" to an app on the Google Play store

    Create an instance by calling GooglePlayEdit.transaction(), instead of using the
    constructor. This can optionally handle committing the transaction when the "with" block
    ends.

    E.g.: `with GooglePlayEdit.transaction() as google_play:`
    """

    def __init__(self, edit_resource, edit_id, package_name):
        self._edit_resource = edit_resource
        self._edit_id = edit_id
        self._package_name = package_name

    def update_app(self, extracted_apks, track, rollout_percentage=None):
        for apk, _ in extracted_apks:
            self.upload_apk(apk)

        version_codes = [metadata['version_code'] for _, metadata in extracted_apks]
        self._update_track(track, version_codes, rollout_percentage)

    def get_track_status(self, track):
        response = self._edit_resource.tracks().get(
            editId=self._edit_id,
            track=track,
            packageName=self._package_name
        ).execute()
        logger.debug('Track "{}" has status: {}'.format(track, response))
        return response

    def upload_apk(self, apk):
        apk_path = apk.name
        logger.info('Uploading "{}" ...'.format(apk_path))
        try:
            response = self._edit_resource.apks().upload(
                editId=self._edit_id,
                packageName=self._package_name,
                media_body=apk_path
            ).execute()
            logger.info('"{}" uploaded'.format(apk_path))
            logger.debug('Upload response: {}'.format(response))
        except HttpError as e:
            if e.resp['status'] == '403':
                # XXX This is really how data is returned by the googleapiclient.
                error_content = json.loads(e.content)
                errors = error_content['error']['errors']
                if (len(errors) == 1 and errors[0]['reason'] in (
                        'apkUpgradeVersionConflict',
                        'apkNotificationMessageKeyUpgradeVersionConflict'
                )):
                    logger.warning(
                        'APK "{}" has already been uploaded on Google Play. Skipping...'.format(
                            apk_path)
                    )
                    return
            raise

    def _update_track(self, track, version_codes, rollout_percentage=None):
        if track == 'rollout' and rollout_percentage is None:
            raise WrongArgumentGiven("To perform a rollout, you must provide the target track "
                                     "(probably 'production') and a rollout_percentage")
        if rollout_percentage is not None:
            if track == 'rollout':
                logger.warn(
                    "track='rollout' is deprecated, assuming you meant 'production'. To avoid "
                    "this message, specify the target track to roll out to (probably 'production'")
                track = 'production'
            if rollout_percentage < 0 or rollout_percentage > 100:
                raise WrongArgumentGiven(
                    'rollout percentage must be between 0 and 100. Value given: {}'.format(
                        rollout_percentage))

            release = {
                u'status': 'inProgress',
                u'userFraction': rollout_percentage / 100.0,  # Ensure float in Python 2
                u'versionCodes': version_codes,
            }
        else:
            release = {
                u'status': 'completed',
                u'versionCodes': version_codes
            }

        body = {
            u'releases': [release],
        }

        response = self._edit_resource.tracks().update(
            editId=self._edit_id, track=track, packageName=self._package_name, body=body
        ).execute()
        logger.info('Track "{}" updated with: {}'.format(track, body))
        logger.debug('Track update response: {}'.format(response))

    def update_listings(self, language, title, full_description, short_description):
        body = {
            'fullDescription': full_description,
            'shortDescription': short_description,
            'title': title,
        }
        response = self._edit_resource.listings().update(
            editId=self._edit_id, packageName=self._package_name, language=language, body=body
        ).execute()
        logger.info(u'Listing for language "{}" has been updated with: {}'.format(language, body))
        logger.debug(u'Listing response: {}'.format(response))

    def update_whats_new(self, language, apk_version_code, whats_new):
        response = self._edit_resource.apklistings().update(
            editId=self._edit_id, packageName=self._package_name, language=language,
            apkVersionCode=apk_version_code, body={'recentChanges': whats_new}
        ).execute()
        logger.info(u'What\'s new listing for ("{}", "{}") has been updated to: "{}"'.format(
            language, apk_version_code, whats_new
        ))
        logger.debug(u'Apk listing response: {}'.format(response))

    @staticmethod
    @contextmanager
    def transaction(service_account, credentials_file_name, package_name, *, contact_server, dry_run):
        edit_resource = _create_google_edit_resource(contact_server, service_account, credentials_file_name)
        edit_id = edit_resource.insert(body={}, packageName=package_name).execute()['id']
        google_play = GooglePlayEdit(edit_resource, edit_id, package_name)
        yield google_play
        if not dry_run:
            edit_resource.commit(editId=edit_id, packageName=package_name).execute()
            logger.info('Changes committed')
            logger.debug('edit_id "{}" for "{}" has been committed'.format(edit_id, package_name))
        else:
            logger.warning('Transaction not committed, since `dry_run` was `True`')


def _create_google_edit_resource(contact_google_play, service_account, credentials_file_name):
    if contact_google_play:
        # Create an httplib2.Http object to handle our HTTP requests an
        # authorize it with the Credentials. Note that the first parameter,
        # service_account_name, is the Email address created for the Service
        # account. It must be the email address associated with the key that
        # was created.
        scope = 'https://www.googleapis.com/auth/androidpublisher'
        credentials = ServiceAccountCredentials.from_p12_keyfile(
            service_account,
            credentials_file_name,
            scopes=scope
        )
        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build(serviceName='androidpublisher', version='v3', http=http,
                        cache_discovery=False)

        return service.edits()
    else:
        logger.warning('Not a single request to Google Play will be made, since `contact_google_play` was set to `False`')
        edit_resource_mock = MagicMock()

        edit_resource_mock.insert = lambda *args, **kwargs: _ExecuteDummy(
            {'id': 'fake-transaction-id'})
        edit_resource_mock.commit = lambda *args, **kwargs: _ExecuteDummy(None)

        apks_mock = MagicMock()
        apks_mock.upload = lambda *args, **kwargs: _ExecuteDummy(
            {'versionCode': 'fake-version-code'})
        edit_resource_mock.apks = lambda *args, **kwargs: apks_mock

        update_mock = MagicMock()
        update_mock.update = lambda *args, **kwargs: _ExecuteDummy('fake-update-response')
        edit_resource_mock.tracks = lambda *args, **kwargs: update_mock
        edit_resource_mock.listings = lambda *args, **kwargs: update_mock
        edit_resource_mock.apklistings = lambda *args, **kwargs: update_mock
        return edit_resource_mock
