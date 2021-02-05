#!/usr/bin/env python
"""iscript constants."""

MAC_PRODUCT_CONFIG = {
    "firefox": {
        "designated_requirements": (
            """=designated => ( """
            """(anchor apple generic and certificate leaf[field.1.2.840.113635.100.6.1.9] ) """
            """or (anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] """
            """and certificate leaf[field.1.2.840.113635.100.6.1.13] and certificate """
            """leaf[subject.OU] = "%(subject_ou)s"))"""
        ),
        "sign_dirs": ("MacOS", "Library"),
        "skip_dirs": tuple(),
        "zipfile_cmd": "zip",
        "create_pkg": True,
    },
    "mozillavpn": {
        "designated_requirements": """=designated => certificate leaf[subject.OU] = "%(subject_ou)s" """,
        "sign_dirs": ("MacOS", "Frameworks"),
        "skip_dirs": ("MozillaVPNLoginItem.app",),
        "zipfile_cmd": "ditto",
        "create_pkg": False,
        "hardened_runtime_files": ["wg", "wireguard-go"],
        "no_entitlements_files": ["wg", "wireguard-go"],
    },
}

PRODUCT_CONFIG = {
    "mac_config": MAC_PRODUCT_CONFIG,
}
