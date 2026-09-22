import hashlib
import logging

import requests

logger = logging.getLogger(__name__)


def load_json_url(url):
    return requests.get(url).json()


def _file_hashsum(hasher, file_path):
    bs = 65536
    with open(file_path, "rb") as fh:
        buf = fh.read(bs)
        while len(buf) > 0:
            hasher.update(buf)
            buf = fh.read(bs)
    return hasher.hexdigest()


def file_sha512sum(file_path):
    return _file_hashsum(hashlib.sha512(), file_path)


def file_sha256sum(file_path):
    return _file_hashsum(hashlib.sha256(), file_path)


def file_md5sum(file_path):
    # vivo's upload interface mandates an MD5; it is an integrity parameter, not a security
    # control, so `usedforsecurity=False` keeps it working where MD5 is policy-restricted.
    return _file_hashsum(hashlib.md5(usedforsecurity=False), file_path)


def filter_out_identical_values(list_):
    return list(set(list_))


def add_push_arguments(parser):
    parser.add_argument("--store", help="Store on which to upload", choices=["google", "samsung", "huawei", "vivo"], default="google")
    parser.add_argument("--secret", help="File that contains google credentials (json). This is only required if the store is google.")
    parser.add_argument("--sgs-service-account-id", help="The service account ID for the samsung galaxy store. This is only required if the store is samsung")
    parser.add_argument("--sgs-access-token", help="The access token for the samsung galaxy store. This is only required if the store is samsung")
    parser.add_argument(
        "--huawei-credentials",
        help="File that contains the huawei app gallery service account credentials (json). This is only required if the store is huawei",
    )
    parser.add_argument("--vivo-access-key", help="The access key for the vivo app store. This is only required if the store is vivo")
    parser.add_argument("--vivo-access-secret", help="The access secret for the vivo app store. This is only required if the store is vivo")
    # `app.update.basic.info` replaces the whole basic-info record rather than patching it,
    # so vivo demands these three; they are normally read back from `app.detail`.
    parser.add_argument(
        "--vivo-language-codes",
        help="Comma-separated vivo language codes (e.g. 'en_in,ms') to use only if the vivo store reports none for the app. "
        "The entry before the first comma becomes the app's default language.",
    )
    parser.add_argument(
        "--vivo-nation-codes",
        help="Comma-separated vivo country codes (e.g. 'in,id') to use only if the vivo store reports none for the app.",
    )
    parser.add_argument("--vivo-email", help="Contact email to use only if the vivo store reports none for the app")
    parser.add_argument(
        "--vivo-scheduled-release-date",
        help="ISO 8601 datetime with a UTC offset (e.g. '2026-10-01T09:00:00Z') to publish at, instead of as soon as "
        "review passes. vivo schedules at most 8 days ahead. Has no effect unless the store is vivo, and requires "
        "--submit.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="After uploading, submit the new binary for release. Has no effect unless the "
        "store is samsung, huawei or vivo. For huawei and vivo this calls the "
        "submit-for-release endpoint; without it the binary is uploaded but left "
        "unsubmitted.",
    )
    parser.add_argument(
        "--do-not-contact-server",
        action="store_false",
        dest="contact_server",
        help="""Prevent any request from reaching the store. Use this option if
you want to run the script without any valid credentials nor valid APKs. --credentials must
still be provided (you can pass a random file name). This overrides --commit: nothing is
uploaded on any store.""",
    )
    parser.add_argument("track", help="Track on which to upload. This has no effect if the store is not google")
    parser.add_argument(
        "--rollout-percentage",
        type=int,
        choices=range(0, 101),
        metavar="[0-100]",
        default=None,
        help="The percentage of user who will get the update. Specify only if track is rollout. The vivo store has no staged rollout and rejects this option.",
    )
    parser.add_argument(
        "--commit",
        action="store_false",
        dest="dry_run",
        help="Actually upload. Required on EVERY store: without it the run stops after the "
        "APK checks and nothing is sent. On google this commits the new release, which "
        "cannot be reverted; on samsung, huawei and vivo it uploads the binaries, and "
        "they are additionally submitted for release only if --submit is given.",
    )


def check_push_arguments(parser, config):
    if config.store == "google":
        if not config.secret:
            parser.error("--secret is mandatory when using --store=google")
    elif config.store == "samsung":
        if not (config.sgs_service_account_id and config.sgs_access_token):
            parser.error("--sgs-service-account-id and --sgs-access-token are mandatory when using --store=samsung")
    elif config.store == "huawei":
        if not config.huawei_credentials:
            parser.error("--huawei-credentials is mandatory when using --store=huawei")
    elif config.store == "vivo":
        if not (config.vivo_access_key and config.vivo_access_secret):
            parser.error("--vivo-access-key and --vivo-access-secret are mandatory when using --store=vivo")


def metadata_by_package_name(metadata_dict):
    package_names = {}
    for file, metadata in metadata_dict.items():
        package_name = metadata["package_name"]
        if package_name not in package_names:
            package_names[package_name] = []
        package_names[package_name].append((file, metadata))

    return package_names
