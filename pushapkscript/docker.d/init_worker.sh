#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

test_var_set APP_DIR

export JARSIGNER_KEY_STORE="$APP_DIR/mozilla-android-keystore"
rm -f "$JARSIGNER_KEY_STORE"
# Generate a temporary password
JARSIGNER_KEY_STORE_PASSWORD=$(openssl rand -hex 30)
CERT_DIR=$APP_DIR/pushapkscript/files

function import_cert() {
        JARSIGNER_KEY_STORE_NAME=$1
        JARSIGNER_KEY_STORE_CERTIFICATE=$2
        echo "Importing $JARSIGNER_KEY_STORE_CERTIFICATE as $JARSIGNER_KEY_STORE_NAME into $JARSIGNER_KEY_STORE"
        keytool \
          -importcert \
          -noprompt \
          -alias $JARSIGNER_KEY_STORE_NAME \
          -file $JARSIGNER_KEY_STORE_CERTIFICATE \
          -keystore $JARSIGNER_KEY_STORE \
          -trustcacerts \
          -storetype jks \
          -srcstorepass $JARSIGNER_KEY_STORE_PASSWORD \
          -deststorepass $JARSIGNER_KEY_STORE_PASSWORD
        keytool \
          -list \
          -v \
          -keystore $JARSIGNER_KEY_STORE \
          -storepass $JARSIGNER_KEY_STORE_PASSWORD
}

case $COT_PRODUCT in
  mobile)
    case $ENV in
      dev|fake-prod)

        echo "dummy" > $CONFIG_DIR/fake_cert.json
        export GOOGLE_CREDENTIALS_REFERENCE_BROWSER_DEP_PATH=$CONFIG_DIR/fake_cert.json

        import_cert reference-browser $CERT_DIR/reference_browser_dep.pem

        ;;
      prod)
        test_var_set 'GOOGLE_SERVICE_ACCOUNT_REFERENCE_BROWSER'

        export GOOGLE_CREDENTIALS_REFERENCE_BROWSER_PATH=$CONFIG_DIR/reference_browser.json

        echo $GOOGLE_SERVICE_ACCOUNT_REFERENCE_BROWSER | base64 -d > $GOOGLE_CREDENTIALS_REFERENCE_BROWSER_PATH

        import_cert reference-browser $CERT_DIR/reference_browser_release.pem
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  firefox)
    case $ENV in
      dev|fake-prod)

        echo "dummy" > $CONFIG_DIR/fake_cert.json
        export GOOGLE_CREDENTIALS_FENIX_DEP_PATH=$CONFIG_DIR/fake_cert.json
        export GOOGLE_CREDENTIALS_FOCUS_DEP_PATH=$CONFIG_DIR/fake_cert.json
        export SGS_SERVICE_ACCOUNT_ID_DEP="0123456"
        export SGS_ACCESS_TOKEN_DEP="dummy"

        import_cert fenix $CERT_DIR/fenix_dep.pem
        import_cert focus $CERT_DIR/focus_dep.pem

        ;;
      prod)
        test_var_set 'GOOGLE_SERVICE_ACCOUNT_FOCUS'
        test_var_set 'GOOGLE_SERVICE_ACCOUNT_FENIX_NIGHTLY'
        test_var_set 'GOOGLE_SERVICE_ACCOUNT_FENIX_BETA'
        test_var_set 'GOOGLE_SERVICE_ACCOUNT_FENIX_RELEASE'
        test_var_set 'SGS_SERVICE_ACCOUNT_ID'
        test_var_set 'SGS_ACCESS_TOKEN'

        export GOOGLE_CREDENTIALS_FOCUS_PATH=$CONFIG_DIR/focus.json
        export GOOGLE_CREDENTIALS_FENIX_NIGHTLY_PATH=$CONFIG_DIR/fenix_nightly.json
        export GOOGLE_CREDENTIALS_FENIX_BETA_PATH=$CONFIG_DIR/fenix_beta.json
        export GOOGLE_CREDENTIALS_FENIX_RELEASE_PATH=$CONFIG_DIR/fenix_release.json

        echo $GOOGLE_SERVICE_ACCOUNT_FOCUS | base64 -d >             $GOOGLE_CREDENTIALS_FOCUS_PATH
        echo $GOOGLE_SERVICE_ACCOUNT_FENIX_NIGHTLY | base64 -d >     $GOOGLE_CREDENTIALS_FENIX_NIGHTLY_PATH
        echo $GOOGLE_SERVICE_ACCOUNT_FENIX_BETA | base64 -d >        $GOOGLE_CREDENTIALS_FENIX_BETA_PATH
        echo $GOOGLE_SERVICE_ACCOUNT_FENIX_RELEASE | base64 -d >     $GOOGLE_CREDENTIALS_FENIX_RELEASE_PATH

        import_cert fenix-nightly $CERT_DIR/fenix_nightly.pem
        import_cert fenix-beta $CERT_DIR/fenix_beta.pem
        import_cert fenix-release $CERT_DIR/fenix_release.pem
        import_cert focus $CERT_DIR/focus_release.pem
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  mozillavpn)
    case $ENV in
      dev|fake-prod)

        echo "dummy" > $CONFIG_DIR/fake_cert.json
        export GOOGLE_CREDENTIALS_MOZILLAVPN_DEP_PATH=$CONFIG_DIR/fake_cert.json

        # no dep signing for mozillavpn yet, so no import_cert
        ;;
      prod)
        test_var_set 'GOOGLE_SERVICE_ACCOUNT_MOZILLAVPN'

        export GOOGLE_CREDENTIALS_MOZILLAVPN_PATH=$CONFIG_DIR/mozillavpn.json
        echo $GOOGLE_SERVICE_ACCOUNT_MOZILLAVPN | base64 -d > $GOOGLE_CREDENTIALS_MOZILLAVPN_PATH

        import_cert mozillavpn $CERT_DIR/mozillavpn.pem
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  *)
    exit 1
    ;;
esac
