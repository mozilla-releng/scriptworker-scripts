import contextlib
import logging
import os

from mozilla_version.version import VersionType
from mozilla_version.gecko import GeckoSnapVersion
from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence, get_hash

from pushsnapscript import task
from pushsnapscript.exceptions import AlreadyLatestError

# XXX Hack to only import a subset of snapcraft. Otherwise snapcraft can't be built on any other
# distribution than Ubuntu. The prod instance runs CentOS 6. There isn't a package version of
# snapcraft on that platform either.
import sys
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_path, 'snapcraft'))
from snapcraft import _store as snapcraft_store_client      # noqa
from snapcraft.storeapi import StoreClient                  # noqa
from snapcraft.storeapi.constants import DEFAULT_SERIES     # noqa
from snapcraft.storeapi.errors import StoreReviewError      # noqa

log = logging.getLogger(__name__)


_VERSION_TYPE_PER_CHANNEL = {
    'edge': VersionType.BETA,
    'beta': VersionType.BETA,
    'candidate': VersionType.RELEASE,
    'stable': VersionType.RELEASE,

    'esr': VersionType.ESR,
    'esr/stable': VersionType.ESR,
    'esr/candidate': VersionType.ESR,
}

# TODO: Parametrize this once we have other products
_SNAP_NAME_ON_STORE = 'firefox'


def push(context, snap_file_path, channel):
    """ Publishes a snap onto a given channel.

    This function performs all the network actions to ensure `snap_file_path` is published on
    `channel`. If `channel` is not whitelisted to contact the Snap Store, then it just early
    returns (this allows staging tasks to not contact the Snap Store instance at all). If allowed,
    this function first connects to the Snap Store, then uploads the Snap onto it. No matter
    whether the snap has already been uploaded, it proceeds to the next step. If the snap is
    already released, then there's nothing to do and the function simply returns. Otherwise, the
    Snap must have a higher version (or build) number to overwrite the existing one. If the version
    number happens to be lower or the same one (while still being a different Snap), then the
    function bails out.

    Args:
        context (scriptworker.context.Context): the scriptworker context. It must define
            `context.config['macaroons_locations'][channel]`.
        snap_file_path (str): The full path to the snap file
        channel (str): The Snap Store channel.
    """
    if not task.is_allowed_to_push_to_snap_store(channel=channel):
        log.warning('Not allowed to push to Snap store. Skipping push...')
        # We don't raise an error because we still want green tasks on dev instances
        return

    macaroon_location = context.config['macaroons_locations'][channel]
    with _store_session(macaroon_location) as store:
        try:
            log.debug('Calling snapcraft.push() with this file: {}'.format(snap_file_path))
            # We don't call store.upload() because this push() does more
            snapcraft_store_client.push(snap_filename=snap_file_path)
        except StoreReviewError as e:
            if 'A file with this exact same content has already been uploaded' in e.additional:
                log.warning(e)
            else:
                raise

        _release_if_needed(store, channel, snap_file_path)


@contextlib.contextmanager
def _store_session(macaroon_location):
    store = StoreClient()

    with open(macaroon_location) as macaroon:
        log.debug('Logging onto Snap store with macaroon file "{}"...'.format(macaroon.name))
        # XXX Bad API. email and password are mandatory in the function signature, but they are
        # read from the macaroon when config_fd is provided
        store.login(email='', password='', config_fd=macaroon)

    log.info('Logged on Snap store')
    try:
        yield store
    finally:
        log.debug('Logging off Snap store...')
        store.logout()
        log.info('Logged off Snap store')


def _release_if_needed(store, channel, snap_file_path):
    # We can't easily know what's the revision and the version of the current and the latest snap.
    # That's why this function fetches all availables revisions, transforms the data, and then
    # finds what's current and latest,
    all_revisions = _list_all_revisions(store)
    metadata_per_revision = _pluck_metadata(all_revisions)
    metadata_per_revision = _filter_versions_that_are_not_the_same_type(metadata_per_revision, channel)
    metadata_per_revision = _populate_sha3_384(store, metadata_per_revision)
    current_sha3_384 = get_hash(snap_file_path, hash_alg='sha3_384')
    current_snap_revision, current_snap_version = _find_revision_and_version_of_current_snap(
        metadata_per_revision, current_sha3_384
    )
    latest_released_revision, latest_released_version = _pick_revision_and_version_of_latest_released_snap(
        channel, metadata_per_revision
    )

    try:
        _check_current_snap_is_not_released(
            current_snap_revision, current_snap_version,
            latest_released_revision, latest_released_version
        )
    except AlreadyLatestError as e:
        # Not raising when Snap is already the latest allows the task to be idempotent.
        # Other errors must raise.
        log.warning(e)
        return

    release_kwargs = {
        'snap_name': _SNAP_NAME_ON_STORE,
        'revision': current_snap_revision,
        'channels': [channel]
    }

    log.debug('Calling store.release() with these kwargs: {}'.format(snap_file_path))
    store.release(**release_kwargs)


def _list_all_revisions(store):
    return store.get_snap_revisions(_SNAP_NAME_ON_STORE)


def _pluck_metadata(snap_revisions):
    return {
        revision['revision']: {
            'version': GeckoSnapVersion.parse(revision['version']),
            'current_channels': revision.get('current_channels', []),
        }
        for revision in snap_revisions
    }


def _filter_versions_that_are_not_the_same_type(metadata_per_revision, channel):
    expected_version_type = _VERSION_TYPE_PER_CHANNEL[channel]

    return {
        revision: revision_metadata
        for revision, revision_metadata in metadata_per_revision.items()
        if revision_metadata['version'].version_type == expected_version_type
    }


def _populate_sha3_384(store, metadata_per_revision):
    return {
        revision: {
            **revision_metadata,
            'download_sha3_384': _get_from_sha3_384_from_revision(store, revision),
        }
        for revision, revision_metadata in metadata_per_revision.items()
        if revision > 1    # First revision doesn't have sha3_384
    }


def _get_from_sha3_384_from_revision(store, revision):
    # Sadly, this function is not exposed in snapcraft.
    headers = store.cpi.get_default_headers()
    headers.update({
        'Accept': 'application/hal+json',
        'X-Ubuntu-Series': DEFAULT_SERIES
    })
    params = {
        'fields': 'status,download_sha3_384,revision',
        'revision': revision
    }
    url = 'api/v1/snaps/details/{}'.format(_SNAP_NAME_ON_STORE)
    resp = store.cpi.get(url, headers=headers, params=params)
    return resp.json()['download_sha3_384']


def _find_revision_and_version_of_current_snap(metadata_per_revision, current_sha3_384):
    # Please note we need to create any new channel manually, first. This can be done by opening
    # a request like this one https://forum.snapcraft.io/t/firefox-please-create-the-track-esr/5006
    # and manually release a snap onto this channel
    item = get_single_item_from_sequence(
        metadata_per_revision.items(),
        lambda item: item[1]['download_sha3_384'] == current_sha3_384,
        ErrorClass=ValueError,
        no_item_error_message='No revision has sha3_384 "{}"'.format(current_sha3_384),
        too_many_item_error_message='Too many revisions have sha3_384 "{}"'.format(current_sha3_384),
    )
    revision = item[0]
    version = item[1]['version']
    log.debug('Current snap (version "{}") found on the store at revision {}'.format(version, revision))
    return revision, version


def _check_current_snap_is_not_released(current_revision, current_version, latest_released_revision, latest_released_version):
    if latest_released_version == current_version:
        if latest_released_revision == current_revision:
            raise AlreadyLatestError(latest_released_version, latest_released_revision)
        else:
            raise TaskVerificationError(
                'Versions "{0}" are the same but revisions differ. This may mean someone shipped a rogue "{0}" before automation! '
                'Latest on store: {1}. Revision of current Snap: {2}'.format(
                    latest_released_version, latest_released_revision, current_revision
                )
            )
    elif latest_released_version > current_version:
        # We don't check if the revision is higher because
        raise TaskVerificationError(
            'Current version "{}" is lower than the latest one released on the store "{}". Downgrades are not allowed.'.format(
                current_version, latest_released_version
            )
        )

    log.debug(
        'Current version "{}" is higher than the latest released one "{}". Okay to release the current one'.format(
            current_version, latest_released_version
        )
    )


def _pick_revision_and_version_of_latest_released_snap(channel, metadata_per_revision):
    item = get_single_item_from_sequence(
        metadata_per_revision.items(),
        lambda item: channel in item[1]['current_channels'],
        ErrorClass=ValueError,
        no_item_error_message='No revision is currently released on channel "{}"'.format(channel),
        too_many_item_error_message='Too many revisions are released on channel "{}"'.format(channel),
    )
    revision = item[0]
    version = item[1]['version']
    log.debug(
        'Found version "{}" (revision {}) to be the latest released on the store'.format(
            version, revision
        )
    )
    return revision, version
