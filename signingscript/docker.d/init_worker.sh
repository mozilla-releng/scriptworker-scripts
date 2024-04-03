#!/bin/bash
set -e errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

#
# Check that all required variables exist
#
test_var_set 'APP_DIR'
test_var_set 'CONFIG_DIR'
test_var_set 'CONFIG_LOADER'
test_var_set 'COT_PRODUCT'
test_var_set 'PROJECT_NAME'
test_var_set 'PUBLIC_IP'
test_var_set 'TEMPLATE_DIR'

export DMG_PATH=$APP_DIR/signingscript/files/dmg
export HFSPLUS_PATH=$APP_DIR/signingscript/files/hfsplus

export PASSWORDS_PATH=$CONFIG_DIR/passwords.json
export APPLE_NOTARIZATION_CREDS_PATH=$CONFIG_DIR/apple_notarization_creds.json
export GPG_PUBKEY_PATH=$APP_DIR/signingscript/src/signingscript/data/gpg_pubkey_dep.asc
export WIDEVINE_CERT_PATH=$CONFIG_DIR/widevine.crt
export AUTHENTICODE_TIMESTAMP_STYLE=old
export AUTHENTICODE_TIMESTAMP_URL=http://timestamp.digicert.com
export AUTHENTICODE_CERT_PATH=$APP_DIR/signingscript/src/signingscript/data/authenticode_dep.crt
export AUTHENTICODE_CERT_PATH_202005=$APP_DIR/signingscript/src/signingscript/data/authenticode_dep.crt
export AUTHENTICODE_CERT_PATH_EV="$AUTHENTICODE_CERT_PATH"
export AUTHENTICODE_CA_PATH=$APP_DIR/signingscript/src/signingscript/data/authenticode_dep_ca.crt
export AUTHENTICODE_CA_PATH_EV="$AUTHENTICODE_CA_PATH"
export AUTHENTICODE_CA_TIMESTAMP_PATH=/usr/lib/ssl/certs/ca-certificates.crt
export AUTHENTICODE_CROSS_CERT_PATH=$APP_DIR/signingscript/src/signingscript/data/authenticode_stub.crt
if [ "$ENV" == "prod" ]; then
  export AUTHENTICODE_TIMESTAMP_STYLE=old
  export AUTHENTICODE_CERT_PATH=$APP_DIR/signingscript/src/signingscript/data/authenticode_prod_202005.crt
  export AUTHENTICODE_CERT_PATH_202005=$APP_DIR/signingscript/src/signingscript/data/authenticode_prod_202005.crt
  export AUTHENTICODE_CERT_PATH_EV=$APP_DIR/signingscript/src/signingscript/data/authenticode_prod_ev.crt
  export AUTHENTICODE_CA_PATH=$APP_DIR/signingscript/src/signingscript/data/authenticode_prod_202005.crt
  export AUTHENTICODE_CA_PATH_EV=$APP_DIR/signingscript/src/signingscript/data/authenticode_prod_ev.crt
  export AUTHENTICODE_CA_TIMESTAMP_PATH=/usr/lib/ssl/certs/ca-certificates.crt
  export GPG_PUBKEY_PATH=$APP_DIR/signingscript/src/signingscript/data/gpg_pubkey_20230505.asc
fi

case $COT_PRODUCT in
  firefox)
    test_var_set 'WIDEVINE_CERT'

    echo $WIDEVINE_CERT | base64 -d > $WIDEVINE_CERT_PATH
    ;;
  thunderbird)
    ;;
  mobile)
    ;;
  app-services)
    ;;
  glean)
    ;;
  xpi)
    ;;
  mozillavpn)
    ;;
  adhoc)
    test_var_set 'WIDEVINE_CERT'

    echo $WIDEVINE_CERT | base64 -d > $WIDEVINE_CERT_PATH
    ;;
  *)
    exit 1
    ;;
esac

case $ENV in
  dev|fake-prod)
    case $COT_PRODUCT in
      firefox|thunderbird)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME'
        test_var_set 'AUTHENTICODE_CERT_PATH'
        test_var_set 'AUTHENTICODE_CERT_PATH_202005'
        test_var_set 'AUTHENTICODE_CA_PATH'
        test_var_set 'AUTHENTICODE_CA_TIMESTAMP_PATH'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'GPG_PUBKEY_PATH'
        test_var_set 'AUTOGRAPH_LANGPACK_PASSWORD'
        test_var_set 'AUTOGRAPH_LANGPACK_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_MAR_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_MAR_USERNAME'
        test_var_set 'AUTOGRAPH_OMNIJA_PASSWORD'
        test_var_set 'AUTOGRAPH_OMNIJA_USERNAME'
        test_var_set 'AUTOGRAPH_WIDEVINE_PASSWORD'
        test_var_set 'AUTOGRAPH_WIDEVINE_USERNAME'
        if [ "$COT_PRODUCT" = "firefox" ]; then
            test_var_set 'AUTOGRAPH_FENIX_PASSWORD'
            test_var_set 'AUTOGRAPH_FENIX_USERNAME'
            test_var_set 'AUTOGRAPH_FOCUS_PASSWORD'
            test_var_set 'AUTOGRAPH_FOCUS_USERNAME'
        fi
        ;;
      mobile)
        test_var_set 'AUTOGRAPH_FENIX_PASSWORD'
        test_var_set 'AUTOGRAPH_FENIX_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_FENIX_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_FENIX_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_FENIX_V3_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_FENIX_V3_USERNAME'
        test_var_set 'AUTOGRAPH_FENIX_MOZILLA_ONLINE_PASSWORD'
        test_var_set 'AUTOGRAPH_FENIX_MOZILLA_ONLINE_USERNAME'
        test_var_set 'AUTOGRAPH_FOCUS_PASSWORD'
        test_var_set 'AUTOGRAPH_FOCUS_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_FOCUS_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_FOCUS_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_FOCUS_V3_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_FOCUS_V3_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'GPG_PUBKEY_PATH'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_PASSWORD'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_USERNAME'
        ;;
      app-services)
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'GPG_PUBKEY_PATH'
        ;;
      glean)
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'GPG_PUBKEY_PATH'
        ;;
      xpi)
        test_var_set 'AUTOGRAPH_XPI_PRIVILEGED_PASSWORD'
        test_var_set 'AUTOGRAPH_XPI_PRIVILEGED_USERNAME'
        ;;
      mozillavpn)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTHENTICODE_CERT_PATH'
        test_var_set 'AUTHENTICODE_CA_PATH'
        test_var_set 'AUTHENTICODE_CA_TIMESTAMP_PATH'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        ;;
      adhoc)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_MAR_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_MAR_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_XPI_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_XPI_USERNAME'
        test_var_set 'GPG_PUBKEY_PATH'
        ;;
    esac
    ;;
  prod)
    case $COT_PRODUCT in
      firefox|thunderbird)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME'
        test_var_set 'AUTHENTICODE_CERT_PATH'
        test_var_set 'AUTHENTICODE_CERT_PATH_202005'
        test_var_set 'AUTHENTICODE_CA_PATH'
        test_var_set 'AUTHENTICODE_CA_TIMESTAMP_PATH'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'GPG_PUBKEY_PATH'
        test_var_set 'AUTOGRAPH_LANGPACK_PASSWORD'
        test_var_set 'AUTOGRAPH_LANGPACK_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_NIGHTLY_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_NIGHTLY_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_RELEASE_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_RELEASE_USERNAME'
        test_var_set 'AUTOGRAPH_OMNIJA_PASSWORD'
        test_var_set 'AUTOGRAPH_OMNIJA_USERNAME'
        test_var_set 'AUTOGRAPH_WIDEVINE_PASSWORD'
        test_var_set 'AUTOGRAPH_WIDEVINE_USERNAME'
        if [ "$COT_PRODUCT" = "firefox" ]; then
            test_var_set 'AUTOGRAPH_FENIX_USERNAME'
            test_var_set 'AUTOGRAPH_FENIX_PASSWORD'
            test_var_set 'AUTOGRAPH_FENIX_MOZILLA_ONLINE_USERNAME'
            test_var_set 'AUTOGRAPH_FENIX_MOZILLA_ONLINE_PASSWORD'
            test_var_set 'AUTOGRAPH_FENNEC_RELEASE_USERNAME'
            test_var_set 'AUTOGRAPH_FENNEC_RELEASE_PASSWORD'
            test_var_set 'AUTOGRAPH_FOCUS_USERNAME'
            test_var_set 'AUTOGRAPH_FOCUS_PASSWORD'
        fi
        ;;
      mobile)
        test_var_set 'AUTOGRAPH_FENNEC_RELEASE_PASSWORD'
        test_var_set 'AUTOGRAPH_FENNEC_RELEASE_USERNAME'
        test_var_set 'AUTOGRAPH_FENIX_PASSWORD'
        test_var_set 'AUTOGRAPH_FENIX_USERNAME'
        test_var_set 'AUTOGRAPH_FOCUS_PASSWORD'
        test_var_set 'AUTOGRAPH_FOCUS_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'GPG_PUBKEY_PATH'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_PASSWORD'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_USERNAME'
        test_var_set 'AUTOGRAPH_STAGE_REFERENCE_BROWSER_PASSWORD'
        test_var_set 'AUTOGRAPH_STAGE_REFERENCE_BROWSER_USERNAME'
        ;;
      app-services)
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'GPG_PUBKEY_PATH'
        ;;
      glean)
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'GPG_PUBKEY_PATH'
        ;;
      xpi)
        test_var_set 'AUTOGRAPH_XPI_PRIVILEGED_PASSWORD'
        test_var_set 'AUTOGRAPH_XPI_PRIVILEGED_USERNAME'
        ;;
      mozillavpn)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME'
        test_var_set 'AUTOGRAPH_MOZILLAVPN_PASSWORD'
        test_var_set 'AUTOGRAPH_MOZILLAVPN_USERNAME'
        test_var_set 'AUTOGRAPH_MOZILLAVPN_ADDONS_PASSWORD'
        test_var_set 'AUTOGRAPH_MOZILLAVPN_ADDONS_USERNAME'
        test_var_set 'AUTHENTICODE_CERT_PATH'
        test_var_set 'AUTHENTICODE_CA_PATH'
        test_var_set 'AUTHENTICODE_CA_TIMESTAMP_PATH'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        ;;
      adhoc)
        test_var_set 'AUTHENTICODE_CERT_PATH_EV'
        test_var_set 'AUTHENTICODE_CA_PATH_EV'
        test_var_set 'AUTHENTICODE_CA_TIMESTAMP_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_EV_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_EV_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_RELEASE_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_RELEASE_USERNAME'
        ;;
    esac
    ;;
  *)
    exit 1
    ;;
esac


$CONFIG_LOADER $TEMPLATE_DIR/passwords.yml $PASSWORDS_PATH
$CONFIG_LOADER $TEMPLATE_DIR/apple_notarization_creds.yml $APPLE_NOTARIZATION_CREDS_PATH
