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
    '.xpi': 'application/x-xpinstall',
    '.apk': 'application/vnd.android.package-archive',
}
STAGE_PLATFORM_MAP = {
    'linux': 'linux-i686',
    'linux64': 'linux-x86_64',
    'macosx64': 'mac',
}
# TODO don't rely on default dict
# use explicit platform 'firefox' mapping when all desktop platforms are added
TEMPLATE_KEY_PLATFORMS = defaultdict(lambda: "firefox", {
    "android-api-15": "fennec",
    "android-api-15-old-id": "fennec",
    "android-api-16": "fennec",
    "android-api-16-old-id": "fennec",
    "android-x86": "fennecx86",
    "android-aarch64": "fennecaarch64",
    "android-x86-old-id": "fennecx86",
})
HASH_BLOCK_SIZE = 1024*1024
INITIAL_RELEASE_PROPS_FILE = "balrog_props.json"
# release buckets don't require a copy of the following artifacts
IGNORED_UPSTREAM_ARTIFACTS = ["balrog_props.json"]

RELEASE_BRANCHES = (
    'mozilla-central',
    'mozilla-beta',
    'mozilla-release',
    'mozilla-esr52'
)

RESTRICTED_BUCKET_PATHS = {
    'nightly': [
        'pub/mobile/nightly',
        'pub/firefox/nightly',
    ],
    'release': [
        'pub/firefox/candidates',
        'pub/firefox/releases',
        'pub/mobile/candidates',
        'pub/mobile/releases',
    ],
    'dep': [
        'pub/firefox/nightly',
        'pub/firefox/candidates',
        'pub/firefox/releases',
        'pub/mobile/nightly',
        'pub/mobile/candidates',
        'pub/mobile/releases',
    ]
}

# actions that imply actual releases, hence the need of `build_number` and
# `version`
RELEASE_ACTIONS = (
    'push-to-candidates',
    'push-to-releases',
)

RELEASE_EXCLUDE = (
    r"^.*tests.*$",
    r"^.*crashreporter.*$",
    r"^.*[^k]\.zip(\.asc)?$",
    r"^.*\.log$",
    r"^.*\.txt$",
    r"^.*/partner-repacks.*$",
    r"^.*.checksums(\.asc)?$",
    r"^.*/logs/.*$",
    r"^.*json$",
    r"^.*/host.*$",
    r"^.*/mar-tools/.*$",
    r"^.*robocop.apk$",
    r"^.*bouncer.apk$",
    r"^.*contrib.*",
    r"^.*/beetmover-checksums/.*$",
)

CACHE_CONTROL_MAXAGE = 3600 * 4
