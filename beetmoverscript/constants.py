from collections import defaultdict

MIME_MAP = {
    '': 'text/plain',
    '.asc': 'text/plain',
    '.beet': 'text/plain',
    '.bundle': 'application/octet-stream',
    '.bz2': 'application/octet-stream',
    '.checksums': 'text/plain',
    '.dmg': 'application/x-iso9660-image',
    '.json': 'application/json',
    '.mar': 'application/octet-stream',
    '.xpi': 'application/zip',
    '.apk': 'application/vnd.android.package-archive',
}
STAGE_PLATFORM_MAP = {
    'linux': 'linux-i686',
    'linux64': 'linux-x86_64',
}
# TODO don't rely on default dict
# use explicit platform 'firefox' mapping when all desktop platforms are added
TEMPLATE_KEY_PLATFORMS = defaultdict(lambda: "firefox", {
    "android-api-15": "fennec",
    "android-x86": "fennecx86"
})
HASH_BLOCK_SIZE = 1024*1024
INITIAL_RELEASE_PROPS_FILE = "balrog_props.json"
# release buckets don't require a copy of the following artifacts
IGNORED_UPSTREAM_ARTIFACTS = ["balrog_props.json"]

RESTRICTED_BUCKET_PATHS = {
    'pub/mobile/nightly': 'nightly',
    'pub/firefox/nightly': 'nightly',
    'pub/mobile/release': 'release',
    'pub/firefox/release': 'release',
}

CHECKSUMS_DIGESTS = ("sha512", "md5", "sha1")
