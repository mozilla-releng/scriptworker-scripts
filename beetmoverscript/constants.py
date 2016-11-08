
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

PLATFORM_MAP = {
    'linux': 'linux-i686',
    'linux64': 'linux-x86_64',
}

MANIFEST_URL_TMPL = "https://queue.taskcluster.net/v1/task/%s/artifacts/public/build/balrog_props.json"
