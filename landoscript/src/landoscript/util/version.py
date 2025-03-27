from mozilla_version.gecko import FirefoxVersion, GeckoVersion, ThunderbirdVersion
from mozilla_version.mobile import MobileVersion

from landoscript.errors import LandoscriptError

# A mapping of bump file prefixes to parsers for their contents.
_VERSION_CLASS_PER_BEGINNING_OF_PATH = {
    "browser/": FirefoxVersion,
    "config/milestone.txt": GeckoVersion,
    "mobile/android/": MobileVersion,
    "mail/": ThunderbirdVersion,
}


def find_what_version_parser_to_use(file):
    version_classes = [cls for path, cls in _VERSION_CLASS_PER_BEGINNING_OF_PATH.items() if file.startswith(path)]

    number_of_version_classes = len(version_classes)
    if number_of_version_classes > 1:
        raise LandoscriptError(f'File "{file}" matched too many classes: {version_classes}')
    if number_of_version_classes > 0:
        return version_classes[0]

    raise LandoscriptError(f"Could not determine version class based on file path for {file}")
