import itertools
import os

import jsone
import pytest
import yaml
from conftest import BASE_DIR

PWD_TEST_VARIABLES = {
    p: "foo"
    for p in (
        "AUTOGRAPH_AUTHENTICODE_EV_PASSWORD",
        "AUTOGRAPH_AUTHENTICODE_EV_USERNAME",
        "AUTOGRAPH_AUTHENTICODE_PASSWORD",
        "AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD",
        "AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME",
        "AUTOGRAPH_AUTHENTICODE_USERNAME",
        "AUTOGRAPH_FENIX_MOZILLA_ONLINE_PASSWORD",
        "AUTOGRAPH_FENIX_MOZILLA_ONLINE_USERNAME",
        "AUTOGRAPH_FENIX_PASSWORD",
        "AUTOGRAPH_FENIX_USERNAME",
        "AUTOGRAPH_STAGE_FENIX_PASSWORD",
        "AUTOGRAPH_STAGE_FENIX_USERNAME",
        "AUTOGRAPH_STAGE_FENIX_V3_PASSWORD",
        "AUTOGRAPH_STAGE_FENIX_V3_USERNAME",
        "AUTOGRAPH_FENNEC_RELEASE_PASSWORD",
        "AUTOGRAPH_FENNEC_RELEASE_USERNAME",
        "AUTOGRAPH_FOCUS_PASSWORD",
        "AUTOGRAPH_FOCUS_USERNAME",
        "AUTOGRAPH_STAGE_FOCUS_PASSWORD",
        "AUTOGRAPH_STAGE_FOCUS_USERNAME",
        "AUTOGRAPH_STAGE_FOCUS_V3_PASSWORD",
        "AUTOGRAPH_STAGE_FOCUS_V3_USERNAME",
        "AUTOGRAPH_GPG_PASSWORD",
        "AUTOGRAPH_GPG_USERNAME",
        "AUTOGRAPH_LANGPACK_PASSWORD",
        "AUTOGRAPH_LANGPACK_USERNAME",
        "AUTOGRAPH_MAR_NIGHTLY_PASSWORD",
        "AUTOGRAPH_MAR_NIGHTLY_USERNAME",
        "AUTOGRAPH_MAR_PASSWORD",
        "AUTOGRAPH_MAR_RELEASE_PASSWORD",
        "AUTOGRAPH_MAR_RELEASE_USERNAME",
        "AUTOGRAPH_MAR_STAGE_PASSWORD",
        "AUTOGRAPH_MAR_STAGE_USERNAME",
        "AUTOGRAPH_MAR_USERNAME",
        "AUTOGRAPH_MOZILLAVPN_ADDONS_PASSWORD",
        "AUTOGRAPH_MOZILLAVPN_ADDONS_USERNAME",
        "AUTOGRAPH_MOZILLAVPN_DEBSIGN_PASSWORD",
        "AUTOGRAPH_MOZILLAVPN_DEBSIGN_USERNAME",
        "AUTOGRAPH_MOZILLAVPN_PASSWORD",
        "AUTOGRAPH_MOZILLAVPN_USERNAME",
        "AUTOGRAPH_OMNIJA_PASSWORD",
        "AUTOGRAPH_OMNIJA_USERNAME",
        "AUTOGRAPH_REFERENCE_BROWSER_PASSWORD",
        "AUTOGRAPH_REFERENCE_BROWSER_USERNAME",
        "AUTOGRAPH_STAGE_REFERENCE_BROWSER_PASSWORD",
        "AUTOGRAPH_STAGE_REFERENCE_BROWSER_USERNAME",
        "AUTOGRAPH_WIDEVINE_PASSWORD",
        "AUTOGRAPH_WIDEVINE_USERNAME",
        "AUTOGRAPH_XPI_PASSWORD",
        "AUTOGRAPH_XPI_USERNAME",
    )
}


PRODUCTS = ("firefox", "thunderbird", "app-services", "glean", "xpi", "mozillavpn", "adhoc")
ENVS = ("dev", "prod", "fake-prod")
# Product of "product" and "env" per file
PARAMS = (
    (
        (
            "apple_notarization_creds.yml",
            {
                "COT_PRODUCT": product,
                "ENV": env,
                "APPLE_NOTARIZATION_ISSUER_ID": "x",
                "APPLE_NOTARIZATION_KEY_ID": "x",
                "APPLE_NOTARIZATION_PRIVATE_KEY": "x",
            },
        ),
        (
            "passwords.yml",
            {
                "COT_PRODUCT": product,
                "ENV": env,
                **PWD_TEST_VARIABLES,
            },
        ),
    )
    for product in PRODUCTS
    for env in ENVS
)
PARAMS = itertools.chain.from_iterable(PARAMS)


@pytest.mark.parametrize("filename,input", PARAMS)
def test_yml_files(filename, input):
    with open(os.path.join(BASE_DIR, "docker.d", filename)) as fd:
        data = yaml.safe_load(fd)
        assert data
        jsone.render(data, input)
