"""Resources that operate on an XPI file."""

import json
from zipfile import ZipFile


def get_langpack_info(path):
    """Extract locale and version from a langpack .xpi."""
    with ZipFile(path, "r") as langpack_xpi:
        manifest = langpack_xpi.getinfo("manifest.json")
        with langpack_xpi.open(manifest) as f:
            contents = f.read().decode("utf-8")
    manifest_info = json.loads(contents)
    browser_specific_settings = manifest_info.get("browser_specific_settings", manifest_info.get("applications", {}))
    langpack_info = {
        "locale": manifest_info["langpack_id"],
        "version": manifest_info["version"],
        "id": browser_specific_settings["gecko"]["id"],
        "unsigned": path,
        "min_version": browser_specific_settings["gecko"]["strict_min_version"],
        "name": manifest_info["name"],
        "description": manifest_info["description"],
    }
    return langpack_info
