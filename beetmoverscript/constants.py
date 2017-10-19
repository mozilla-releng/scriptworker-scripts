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
    'win32': 'win32',
    'win64': 'win64',
}
TEMPLATE_KEY_PLATFORMS = {
    "android-api-15": "fennec",
    "android-api-15-old-id": "fennec",
    "android-api-16": "fennec",
    "android-api-16-old-id": "fennec",
    "android-x86": "fennecx86",
    "android-aarch64": "fennecaarch64",
    "android-x86-old-id": "fennecx86",
    "linux": "firefox",
    "linux64": "firefox",
    "macosx64": "firefox",
    "win32": "firefox",
    "win64": "firefox",
    "linux-devedition": "devedition",
    "linux64-devedition": "devedition",
    "macosx64-devedition": "devedition",
    "win32-devedition": "devedition",
    "win64-devedition": "devedition",
}
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
        'pub/devedition/nightly',
    ],
    'release': [
        'pub/devedition/candidates',
        'pub/devedition/releases',
        'pub/firefox/candidates',
        'pub/firefox/releases',
        'pub/mobile/candidates',
        'pub/mobile/releases',
    ],
    'dep': [
        'pub/devedition/nightly',
        'pub/devedition/candidates',
        'pub/devedition/releases',
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

# XXX this is a fairly clunky way of specifying which files to copy from
# candidates to releases -- let's find a nicer way of doing this.
# XXX if we keep this, let's make it configurable? overridable in config?
# Faster to update a config file in puppet than to ship a new beetmover release
# and update in puppet
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
