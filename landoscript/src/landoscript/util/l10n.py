from dataclasses import dataclass
from pathlib import Path

from moz.l10n.paths import L10nConfigPaths, get_android_locale


@dataclass
class L10nFile:
    src_name: str
    dst_name: str


def getL10nFilesFromToml(toml_path, toml_contents, force_paths=[]):
    """Extract list of localized files from project configuration (TOML)"""

    def load(_):
        return toml_contents

    project_config_paths = L10nConfigPaths(toml_path, cfg_load=load, locale_map={"android_locale": get_android_locale}, force_paths=force_paths)

    l10n_files = []
    locales = list(project_config_paths.all_locales)
    locales.sort()

    tgt_paths = [tgt_path for _, tgt_path in project_config_paths.all()]
    for locale in locales:
        # Exclude missing files
        for tgt_path in tgt_paths:
            path = project_config_paths.format_target_path(tgt_path, locale)
            l10n_files.append(Path(path))

    return l10n_files
