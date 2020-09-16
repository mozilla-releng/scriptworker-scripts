"""Resources that operate on an XPI file."""

import json
import re
from zipfile import ZipFile

from addonscript.exceptions import BadVersionError


def get_stripped_version(version):
    """Strip out buildid or other extraneous info from the version

    Args:
        version (string): the full version string from manifest.json
                          e.g. `81.0buildid20200914232702`
    Returns:
        string: semver version
    """
    m = re.match(r"""[0-9\.]+""", version)
    if m:
        return m.group(0)
    else:
        raise BadVersionError(f"Can't determine stripped version from `{version}`!")


def get_langpack_info(path):
    """Extract locale and version from a langpack .xpi."""
    with ZipFile(path, "r") as langpack_xpi:
        manifest = langpack_xpi.getinfo("manifest.json")
        with langpack_xpi.open(manifest) as f:
            contents = f.read().decode("utf-8")
    manifest_info = json.loads(contents)
    langpack_info = {
        "locale": manifest_info["langpack_id"],
        "version": manifest_info["version"],
        "id": manifest_info["applications"]["gecko"]["id"],
        "unsigned": path,
        "min_version": manifest_info["applications"]["gecko"].get("strict_min_version", get_stripped_version(manifest_info["version"])),
    }
    return langpack_info
