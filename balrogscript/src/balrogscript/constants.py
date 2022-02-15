"""Balrogscript constants.

Attributes:
    VALID_ACTIONS (tuple): the available actions supported by balrogscript.

"""
VALID_ACTIONS = (
    "submit-locale",
    "submit-toplevel",
    "schedule",
    "set-readonly",
    "v2-submit-locale",
    "v2-submit-toplevel",
    "submit-system-addons",
)

SYSTEM_ADDONS_PLATFORMS = {
    "Darwin_x86-gcc3": {
        "alias": "default",
    },
    "Darwin_x86_64-gcc3": {"alias": "default"},
    "Darwin_x86-gcc3-u-i386-x86_64": {"alias": "default"},
    "Darwin_x86_64-gcc3-u-i386-x86_64": {"alias": "default"},
    "Linux_x86-gcc3": {"alias": "default"},
    "Linux_x86_64-gcc3": {"alias": "default"},
    "WINNT_x86-msvc": {"alias": "default"},
    "WINNT_x86-msvc-x64": {"alias": "default"},
    "WINNT_x86-msvc-x86": {"alias": "default"},
    "WINNT_x86_64-msvc": {"alias": "default"},
    "WINNT_x86_64-msvc-x64": {"alias": "default"},
}
