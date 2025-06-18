import hashlib
import logging
import requests

logger = logging.getLogger(__name__)


def load_json_url(url):
    return requests.get(url).json()


def file_sha512sum(file_path):
    bs = 65536
    hasher = hashlib.sha512()
    with open(file_path, 'rb') as fh:
        buf = fh.read(bs)
        while len(buf) > 0:
            hasher.update(buf)
            buf = fh.read(bs)
    return hasher.hexdigest()


def filter_out_identical_values(list_):
    return list(set(list_))


def add_push_arguments(parser):
    parser.add_argument('--store', help='Store on which to upload', choices=['google', 'samsung'], default="google")
    parser.add_argument('--secret', help='File that contains google credentials (json). This is only required if the store is google.')
    parser.add_argument('--sgs-service-account-id', help='The service account ID for the samsung galaxy store. This is only required if the store is samsung')
    parser.add_argument('--sgs-access-token', help='The access token for the samsung galaxy store. This is only required if the store is samsung')
    parser.add_argument('--submit', help='Submit the submission for review. This doesn\'t change anything unless the store is samsung', action='store_true')
    parser.add_argument('--do-not-contact-server', action='store_false', dest='contact_server',
                        help='''Prevent any request to reach the APK server. Use this option if
you want to run the script without any valid credentials nor valid APKs. --credentials must
still be provided (you can pass a random file name).''')
    parser.add_argument('track', help='Track on which to upload. This has no effect if the store is not google')
    parser.add_argument(
        '--rollout-percentage',
        type=int,
        choices=range(0, 101),
        metavar='[0-100]',
        default=None,
        help='The percentage of user who will get the update. Specify only if track is rollout'
    )
    parser.add_argument('--commit', action='store_false', dest='dry_run',
                        help='Commit new release on Google Play. This action cannot be reverted. This has no effect if the store is not google')


def check_push_arguments(parser, config):
    if config.store == 'google':
        if not config.secret:
            parser.error("--secret is mandatory when using --store=google")
    elif config.store == 'samsung':
        if not (config.sgs_service_account_id and config.sgs_access_token):
            parser.error('--sgs-service-account-id and --sgs-access-token are mandatory when using --store=samsung')


def metadata_by_package_name(metadata_dict):
    package_names = {}
    for (file, metadata) in metadata_dict.items():
        package_name = metadata['package_name']
        if package_name not in package_names:
            package_names[package_name] = []
        package_names[package_name].append((file, metadata))

    return package_names
