from contextlib import contextmanager

import json
import logging

import httplib2

from apiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
# HACK: importing mock in production is useful for option `--do-not-contact-google-play`
from unittest.mock import MagicMock

from mozapkpublisher.common.exceptions import WrongArgumentGiven

logger = logging.getLogger(__name__)

NUM_RETRIES = 3


def add_general_google_play_arguments(parser):
    parser.add_argument('--credentials', dest='google_play_credentials_filename',
                        help='The json authentication file', required=True)

    parser.add_argument('--commit', action='store_true',
                        help='Commit changes onto Google Play. This action cannot be reverted.')
    parser.add_argument('--do-not-contact-google-play', action='store_false', dest='contact_google_play',
                        help='''Prevent any request to reach Google Play. Use this option if you want to run the script
without any valid credentials nor valid APKs. In fact, Google Play may error out at the first invalid piece of data sent.
--credentials must still be provided (you can pass a random file name).''')


class _ExecuteDummy:
    def __init__(self, return_value):
        self._return_value = return_value

    def execute(self, **kwargs):
        return self._return_value


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

    def update_aab(self, extracted_aabs, track, rollout_percentage=None):
        for aab, _ in extracted_aabs:
            self.upload_aab(aab)

        version_codes = [metadata['version_code'] for _, metadata in extracted_aabs]
        self._update_track(track, version_codes, rollout_percentage)

    def get_track_status(self, track):
        response = self._edit_resource.tracks().get(
            editId=self._edit_id,
            track=track,
            packageName=self._package_name
        ).execute(num_retries=NUM_RETRIES)
        logger.debug('Track "{}" has status: {}'.format(track, response))
        return response

    def upload_apk(self, apk):
        apk_path = apk.name
        logger.info('Uploading "{}" ...'.format(apk_path))
        try:
            response = self._edit_resource.apks().upload(
                editId=self._edit_id,
                packageName=self._package_name,
                media_body=apk_path,
                # Seems like mime type need not be specified for apk files:
                # media_mime_type='application/octet-stream',
            ).execute(num_retries=NUM_RETRIES)
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

    def upload_aab(self, aab):
        # try to get extra network diagnostics during upload
        debuglevel = httplib2.debuglevel
        httplib2.debuglevel = 4

        aab_path = aab.name
        logger.info('Uploading "{}" ...'.format(aab_path))
        try:
            response = self._edit_resource.bundles().upload(
                editId=self._edit_id,
                packageName=self._package_name,
                media_body=aab_path,
                media_mime_type='application/octet-stream',
            ).execute(num_retries=NUM_RETRIES)
            logger.info('"{}" uploaded'.format(aab_path))
            logger.debug('Upload response: {}'.format(response))
        except Exception:
            logger.exception("caught exception in upload_aab:")
            raise
        finally:
            httplib2.debuglevel = debuglevel

    def _update_track(self, track, version_codes, rollout_percentage=None):
        if track == 'rollout' and rollout_percentage is None:
            raise WrongArgumentGiven("To perform a rollout, you must provide the target track "
                                     "(probably 'production') and a rollout_percentage")
        if rollout_percentage is not None:
            if track == 'rollout':
                logger.warning(
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
            u'track': track,
        }

        response = self._edit_resource.tracks().update(
            editId=self._edit_id, track=track, packageName=self._package_name, body=body
        ).execute(num_retries=NUM_RETRIES)
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
        ).execute(num_retries=NUM_RETRIES)
        logger.info(u'Listing for language "{}" has been updated with: {}'.format(language, body))
        logger.debug(u'Listing response: {}'.format(response))

    def update_whats_new(self, language, apk_version_code, whats_new):
        response = self._edit_resource.apklistings().update(
            editId=self._edit_id, packageName=self._package_name, language=language,
            apkVersionCode=apk_version_code, body={'recentChanges': whats_new}
        ).execute(num_retries=NUM_RETRIES)
        logger.info(u'What\'s new listing for ("{}", "{}") has been updated to: "{}"'.format(
            language, apk_version_code, whats_new
        ))
        logger.debug(u'Apk listing response: {}'.format(response))

    @staticmethod
    @contextmanager
    def transaction(credentials_file_name, package_name, *, contact_server, dry_run):
        edit_resource = _create_google_edit_resource(contact_server, credentials_file_name)
        edit_id = edit_resource.insert(body={}, packageName=package_name).execute(num_retries=NUM_RETRIES)['id']
        google_play = GooglePlayEdit(edit_resource, edit_id, package_name)
        yield google_play
        if not dry_run:
            edit_resource.commit(editId=edit_id, packageName=package_name).execute(num_retries=NUM_RETRIES)
            logger.info('Changes committed')
            logger.debug('edit_id "{}" for "{}" has been committed'.format(edit_id, package_name))
        else:
            logger.warning('Transaction not committed, since `dry_run` was `True`')


def _create_google_edit_resource(contact_google_play, credentials_file_name):
    if contact_google_play:
        scope = 'https://www.googleapis.com/auth/androidpublisher'
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file_name,
            scopes=[scope],
        )

        service = build(serviceName='androidpublisher', version='v3',
                        credentials=credentials,
                        cache_discovery=False,
                        num_retries=NUM_RETRIES)

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

        bundles_mock = MagicMock()
        bundles_mock.upload = lambda *args, **kwargs: _ExecuteDummy(
            {'versionCode': 'fake-version-code'})
        edit_resource_mock.bundles = lambda *args, **kwargs: bundles_mock

        update_mock = MagicMock()
        update_mock.update = lambda *args, **kwargs: _ExecuteDummy('fake-update-response')
        edit_resource_mock.tracks = lambda *args, **kwargs: update_mock
        edit_resource_mock.listings = lambda *args, **kwargs: update_mock
        edit_resource_mock.apklistings = lambda *args, **kwargs: update_mock
        return edit_resource_mock
