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
test_var_set 'CONFIG_DIR'
test_var_set 'CONFIG_LOADER'
test_var_set 'COT_PRODUCT'
test_var_set 'GPG_PUBKEY'
test_var_set 'PROJECT_NAME'
test_var_set 'PUBLIC_IP'
test_var_set 'TEMPLATE_DIR'

export DMG_PATH=/app/signingscript/files/dmg
export HFSPLUS_PATH=/app/signingscript/files/hfsplus
export ZIPALIGN_PATH=/usr/bin/zipalign

export PASSWORDS_PATH=$CONFIG_DIR/passwords.json
export GPG_PUBKEY_PATH=$CONFIG_DIR/gpg_pubkey
export WIDEVINE_CERT_PATH=$CONFIG_DIR/widevine.crt
export AUTHENTICODE_TIMESTAMP_STYLE=null
export AUTHENTICODE_CERT_PATH=/app/signingscript/src/signingscript/data/authenticode_dep.crt
export AUTHENTICODE_CERT_PATH_202005=/app/signingscript/src/signingscript/data/authenticode_dep.crt
export AUTHENTICODE_CERT_PATH_202104=/app/signingscript/src/signingscript/data/authenticode_dep.crt
export AUTHENTICODE_CROSS_CERT_PATH=/app/signingscript/src/signingscript/data/authenticode_stub.crt
if [ "$ENV" == "prod" ]; then
  export AUTHENTICODE_TIMESTAMP_STYLE=old
  export AUTHENTICODE_CERT_PATH=/app/signingscript/src/signingscript/data/authenticode_prod_202005.crt
  export AUTHENTICODE_CERT_PATH_202005=/app/signingscript/src/signingscript/data/authenticode_prod_202005.crt
  export AUTHENTICODE_CERT_PATH_202104=/app/signingscript/src/signingscript/data/authenticode_prod_202104.crt
fi

echo $GPG_PUBKEY | base64 -d > $GPG_PUBKEY_PATH

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
  mpd001)
    export AUTHENTICODE_CERT_PATH=/app/signingscript/src/signingscript/data/authenticode_mpd_dep.crt
    if [ "$ENV" == "prod" ]; then
      export AUTHENTICODE_CERT_PATH=/app/signingscript/src/signingscript/data/authenticode_mpd_prod.crt
    fi
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
        test_var_set 'AUTHENTICODE_CERT_PATH_202104'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        test_var_set 'AUTOGRAPH_FENNEC_PASSWORD'
        test_var_set 'AUTOGRAPH_FENNEC_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_LANGPACK_PASSWORD'
        test_var_set 'AUTOGRAPH_LANGPACK_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_STAGE_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_STAGE_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_USERNAME'
        test_var_set 'AUTOGRAPH_OMNIJA_PASSWORD'
        test_var_set 'AUTOGRAPH_OMNIJA_USERNAME'
        test_var_set 'AUTOGRAPH_WIDEVINE_PASSWORD'
        test_var_set 'AUTOGRAPH_WIDEVINE_USERNAME'
        ;;
      mobile)
        test_var_set 'AUTOGRAPH_FENIX_PASSWORD'
        test_var_set 'AUTOGRAPH_FENIX_USERNAME'
        test_var_set 'AUTOGRAPH_FOCUS_PASSWORD'
        test_var_set 'AUTOGRAPH_FOCUS_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_PASSWORD'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_USERNAME'
        ;;
      app-services)
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        ;;
      glean)
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        ;;
      xpi)
        test_var_set 'AUTOGRAPH_XPI_PASSWORD'
        test_var_set 'AUTOGRAPH_XPI_USERNAME'
        ;;
      mpd001)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTHENTICODE_CERT_PATH'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        ;;
      adhoc)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_STAGE_PASSWORD'
        test_var_set 'AUTOGRAPH_MAR_STAGE_USERNAME'
        test_var_set 'AUTOGRAPH_MAR_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
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
        test_var_set 'AUTHENTICODE_CERT_PATH_202104'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
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
        ;;
      mobile)
        test_var_set 'AUTOGRAPH_FENNEC_RELEASE_PASSWORD'
        test_var_set 'AUTOGRAPH_FENNEC_RELEASE_USERNAME'
        test_var_set 'AUTOGRAPH_FIREFOX_TV_USERNAME'
        test_var_set 'AUTOGRAPH_FIREFOX_TV_PASSWORD'
        test_var_set 'AUTOGRAPH_FENIX_PASSWORD'
        test_var_set 'AUTOGRAPH_FENIX_USERNAME'
        test_var_set 'AUTOGRAPH_FOCUS_PASSWORD'
        test_var_set 'AUTOGRAPH_FOCUS_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_PASSWORD'
        test_var_set 'AUTOGRAPH_REFERENCE_BROWSER_USERNAME'
        ;;
      app-services)
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        ;;
      glean)
        test_var_set 'AUTOGRAPH_GPG_USERNAME'
        test_var_set 'AUTOGRAPH_GPG_PASSWORD'
        ;;
      xpi)
        test_var_set 'AUTOGRAPH_XPI_PASSWORD'
        test_var_set 'AUTOGRAPH_XPI_USERNAME'
        ;;
      mpd001)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_EV_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_EV_USERNAME'
        test_var_set 'AUTHENTICODE_CERT_PATH'
        test_var_set 'AUTHENTICODE_CROSS_CERT_PATH'
        test_var_set 'AUTHENTICODE_TIMESTAMP_STYLE'
        ;;
      adhoc)
        test_var_set 'AUTOGRAPH_AUTHENTICODE_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_USERNAME'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_PASSWORD'
        test_var_set 'AUTOGRAPH_AUTHENTICODE_SHA2_USERNAME'
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
