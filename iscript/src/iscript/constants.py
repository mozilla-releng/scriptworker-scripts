#!/usr/bin/env python
"""iscript constants."""

# Autograph key ids used - must match signinscript config
# See signingscript/docker.d/passwords.yml
LANGPACK_AUTOGRAPH_KEY_ID = {
    "nightly": "webextensions_rsa_202404",
    "release": "webextensions_rsa_202404",
    "dep": "webextensions_rsa_dep_202402",
}

OMNIJA_AUTOGRAPH_KEY_ID = {
    "nightly": "systemaddon_rsa_rel_202404",
    "release": "systemaddon_rsa_rel_202404",
    "dep": "systemaddon_rsa_dep_202402",
}

MAC_PRODUCT_CONFIG = {
    "firefox": {
        "designated_requirements": (
            """=designated => """
            """anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] """
            """and certificate leaf[field.1.2.840.113635.100.6.1.13] and certificate """
            """leaf[subject.OU] = "%(subject_ou)s" """
        ),
        "sign_dirs": ("MacOS", "Library", "Frameworks"),
        "skip_dirs": tuple(),
        "zipfile_cmd": "zip",
        "create_pkg": True,
        "hardened_runtime_only_files": "geckodriver",
    },
    "mozillavpn": {
        "designated_requirements": """=designated => certificate leaf[subject.OU] = "%(subject_ou)s" """,
        "sign_dirs": ("MacOS", "Frameworks", "Resources"),
        "skip_dirs": ("MozillaVPNLoginItem.app", "utils"),
        "zipfile_cmd": "ditto",
        "create_pkg": False,
        "hardened_runtime_only_files": ["wg", "wireguard-go"],
    },
    "mozregression": {
        "designated_requirements": """=designated => certificate leaf[subject.OU] = "%(subject_ou)s" """,
        "sign_dirs": ("MacOS", "Frameworks", "Resources"),
        "skip_dirs": tuple(),
        "zipfile_cmd": "ditto",
        "create_pkg": False,
        "hardened_runtime_only_files": tuple(),
    },
}

PRODUCT_CONFIG = {
    "mac_config": MAC_PRODUCT_CONFIG,
}
