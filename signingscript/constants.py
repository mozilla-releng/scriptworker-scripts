#!/usr/bin/env python
"""Signingscript constants module."""

AUTOGRAPH_CUSTOM_APK_FORMATS = {
    'autograph_fennec_sha1': 'SHA1',
    'autograph_fennec_sha256': 'SHA256',
    'autograph_fennec_sha384': 'SHA384',
    'autograph_fennec_sha512': 'SHA512'
}

AUTOGRAPH_APK_FORMATS = [
    *AUTOGRAPH_CUSTOM_APK_FORMATS.keys(),
    'autograph_fennec',
    'autograph_focus'
]
