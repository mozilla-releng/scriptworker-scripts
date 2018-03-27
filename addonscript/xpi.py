import json
from zipfile import ZipFile


def get_langpack_info(context, path):
    """Extract locale and version from a langpack .xpi"""
    with ZipFile(path, 'r') as langpack_xpi:
        manifest = langpack_xpi.getinfo('manifest.json')
        with langpack_xpi.open(manifest) as f:
            contents = f.read().decode('utf-8')
    manifest_info = json.loads(contents)
    langpack_info = {
        'locale': manifest_info['langpack_id'],
        'version': manifest_info['version'],
        'id': manifest_info['applications']['gecko']['id'],
        'unsigned': path,
    }
    return langpack_info
