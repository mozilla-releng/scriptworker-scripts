#!/bin/bash
set -e

#
# Check that all required variables exist
#
test $CONFIG_DIR
test $CONFIG_LOADER
test $COT_PRODUCT
test $GPG_PUBKEY
test $PROJECT_NAME
test $PUBLIC_IP
test $TEMPLATE_DIR

export DMG_PATH=/app/files/dmg
export HFSPLUS_PATH=/app/files/hfsplus
export ZIPALIGN_PATH=/usr/bin/zipalign

export PASSWORDS_PATH=$CONFIG_DIR/passwords.json
export SIGNTOOL_PATH="/app/bin/signtool"
export SSL_CERT_PATH="/app/src/signingscript/data/host.cert"
export GPG_PUBKEY_PATH=$CONFIG_DIR/gpg_pubkey
export WIDEVINE_CERT_PATH=$CONFIG_DIR/widevine.crt
export AUTHENTICODE_TIMESTAMP_STYLE=null
export AUTHENTICODE_CERT_PATH=/app/src/signingscript/data/authenticode_dep.crt
export AUTHENTICODE_CROSS_CERT_PATH=/app/src/signingscript/data/authenticode_stub.crt
if [ "$ENV" == "prod" ]; then
  export AUTHENTICODE_TIMESTAMP_STYLE=old
  export AUTHENTICODE_CERT_PATH=/app/src/signingscript/data/authenticode_prod.crt
fi

echo $GPG_PUBKEY | base64 -d > $GPG_PUBKEY_PATH

case $COT_PRODUCT in
  firefox)
    test $WIDEVINE_CERT

    echo $WIDEVINE_CERT | base64 -d > $WIDEVINE_CERT_PATH
    ;;
  thunderbird)
    ;;
  mobile)
    ;;
  application-services)
    ;;
  *)
    exit 1
    ;;
esac

case $ENV in
  dev)
    test $AUTOGRAPH_AUTHENTICODE_PASSWORD
    test $AUTOGRAPH_AUTHENTICODE_USERNAME
    test $AUTHENTICODE_CERT_PATH
    test $AUTHENTICODE_CROSS_CERT_PATH
    test $AUTHENTICODE_TIMESTAMP_STYLE
    test $AUTOGRAPH_FENNEC_PASSWORD
    test $AUTOGRAPH_FENNEC_USERNAME
    test $AUTOGRAPH_GPG_PASSWORD
    test $AUTOGRAPH_GPG_USERNAME
    test $AUTOGRAPH_LANGPACK_PASSWORD
    test $AUTOGRAPH_LANGPACK_USERNAME
    test $AUTOGRAPH_MAR_PASSWORD
    test $AUTOGRAPH_MAR_STAGE_PASSWORD
    test $AUTOGRAPH_MAR_STAGE_USERNAME
    test $AUTOGRAPH_MAR_USERNAME
    test $AUTOGRAPH_OMNIJA_PASSWORD
    test $AUTOGRAPH_OMNIJA_USERNAME
    test $AUTOGRAPH_WIDEVINE_PASSWORD
    test $AUTOGRAPH_WIDEVINE_USERNAME
    ;;
  fake-prod)
    case $COT_PRODUCT in
      firefox|thunderbird)
        test $AUTOGRAPH_AUTHENTICODE_PASSWORD
        test $AUTOGRAPH_AUTHENTICODE_USERNAME
        test $AUTHENTICODE_CERT_PATH
        test $AUTHENTICODE_CROSS_CERT_PATH
        test $AUTHENTICODE_TIMESTAMP_STYLE
        test $AUTOGRAPH_FENNEC_PASSWORD
        test $AUTOGRAPH_FENNEC_USERNAME
        test $AUTOGRAPH_GPG_PASSWORD
        test $AUTOGRAPH_GPG_USERNAME
        test $AUTOGRAPH_LANGPACK_PASSWORD
        test $AUTOGRAPH_LANGPACK_USERNAME
        test $AUTOGRAPH_MAR_PASSWORD
        test $AUTOGRAPH_MAR_STAGE_PASSWORD
        test $AUTOGRAPH_MAR_STAGE_USERNAME
        test $AUTOGRAPH_MAR_USERNAME
        test $AUTOGRAPH_OMNIJA_PASSWORD
        test $AUTOGRAPH_OMNIJA_USERNAME
        test $AUTOGRAPH_WIDEVINE_PASSWORD
        test $AUTOGRAPH_WIDEVINE_USERNAME
        ;;
      mobile)
        test $AUTOGRAPH_FENIX_PASSWORD
        test $AUTOGRAPH_FENIX_USERNAME
        test $AUTOGRAPH_FOCUS_PASSWORD
        test $AUTOGRAPH_FOCUS_USERNAME
        test $AUTOGRAPH_GPG_PASSWORD
        test $AUTOGRAPH_GPG_USERNAME
        test $AUTOGRAPH_REFERENCE_BROWSER_PASSWORD
        test $AUTOGRAPH_REFERENCE_BROWSER_USERNAME
        ;;
      application-services)
        test $AUTOGRAPH_GPG_PASSWORD
        test $AUTOGRAPH_GPG_USERNAME
        ;;
    esac
    ;;
  prod)
    case $COT_PRODUCT in
      firefox|thunderbird)
        test $AUTOGRAPH_AUTHENTICODE_PASSWORD
        test $AUTOGRAPH_AUTHENTICODE_USERNAME
        test $AUTHENTICODE_CERT_PATH
        test $AUTHENTICODE_CROSS_CERT_PATH
        test $AUTHENTICODE_TIMESTAMP_STYLE
        test $AUTOGRAPH_FENNEC_NIGHTLY_PASSWORD
        test $AUTOGRAPH_FENNEC_NIGHTLY_USERNAME
        test $AUTOGRAPH_FENNEC_RELEASE_PASSWORD
        test $AUTOGRAPH_FENNEC_RELEASE_USERNAME
        test $AUTOGRAPH_GPG_PASSWORD
        test $AUTOGRAPH_GPG_PASSWORD
        test $AUTOGRAPH_GPG_USERNAME
        test $AUTOGRAPH_GPG_USERNAME
        test $AUTOGRAPH_LANGPACK_PASSWORD
        test $AUTOGRAPH_LANGPACK_USERNAME
        test $AUTOGRAPH_MAR_NIGHTLY_PASSWORD
        test $AUTOGRAPH_MAR_NIGHTLY_USERNAME
        test $AUTOGRAPH_MAR_RELEASE_PASSWORD
        test $AUTOGRAPH_MAR_RELEASE_USERNAME
        test $AUTOGRAPH_OMNIJA_PASSWORD
        test $AUTOGRAPH_OMNIJA_USERNAME
        test $AUTOGRAPH_WIDEVINE_PASSWORD
        test $AUTOGRAPH_WIDEVINE_USERNAME
        ;;
      mobile)
        test $AUTOGRAPH_FENIX_BETA_PASSWORD
        test $AUTOGRAPH_FENIX_BETA_USERNAME
        test $AUTOGRAPH_FENIX_NIGHTLY_PASSWORD
        test $AUTOGRAPH_FENIX_NIGHTLY_USERNAME
        test $AUTOGRAPH_FENIX_PASSWORD
        test $AUTOGRAPH_FENIX_USERNAME
        test $AUTOGRAPH_FOCUS_PASSWORD
        test $AUTOGRAPH_FOCUS_USERNAME
        test $AUTOGRAPH_GPG_PASSWORD
        test $AUTOGRAPH_GPG_USERNAME
        test $AUTOGRAPH_REFERENCE_BROWSER_PASSWORD
        test $AUTOGRAPH_REFERENCE_BROWSER_USERNAME
        ;;
      application-services)
        test $AUTOGRAPH_GPG_USERNAME
        test $AUTOGRAPH_GPG_PASSWORD
        ;;
    esac
    ;;
  *)
    exit 1
    ;;
esac


$CONFIG_LOADER $TEMPLATE_DIR/passwords.yml $PASSWORDS_PATH
