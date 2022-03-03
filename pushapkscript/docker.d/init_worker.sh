#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

export JARSIGNER_KEY_STORE="/app/mozilla-android-keystore"
rm -f "$JARSIGNER_KEY_STORE"
# Generate a temporary password
JARSIGNER_KEY_STORE_PASSWORD=$(openssl rand -hex 30)
CERT_DIR=/app/pushapkscript/files

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
  firefox)
    case $ENV in
      dev|fake-prod)
        test_var_set 'GOOGLE_CREDENTIALS_FIREFOX_DEP'
        export GOOGLE_CREDENTIALS_FIREFOX_DEP_PATH=$CONFIG_DIR/dep.p12
        echo $GOOGLE_CREDENTIALS_FIREFOX_DEP | base64 -d > $GOOGLE_CREDENTIALS_FIREFOX_DEP_PATH

        import_cert dep $CERT_DIR/dep.pem
        ;;
      prod)
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  mobile)
    case $ENV in
      dev|fake-prod)

        echo "dummy" > $CONFIG_DIR/fake_cert.p12
        export GOOGLE_CREDENTIALS_FENIX_DEP_PATH=$CONFIG_DIR/fake_cert.p12
        export GOOGLE_CREDENTIALS_FOCUS_DEP_PATH=$CONFIG_DIR/fake_cert.p12
        export GOOGLE_CREDENTIALS_REFERENCE_BROWSER_DEP_PATH=$CONFIG_DIR/fake_cert.p12

        import_cert fenix $CERT_DIR/fenix_dep.pem
        import_cert focus $CERT_DIR/focus_dep.pem
        import_cert reference-browser $CERT_DIR/reference_browser_dep.pem

        ;;
      prod)
        test_var_set 'GOOGLE_PLAY_SERVICE_ACCOUNT_FENIX_PROD'
        test_var_set 'GOOGLE_CREDENTIALS_FENIX_PROD'
        test_var_set 'GOOGLE_PLAY_SERVICE_ACCOUNT_FOCUS'
        test_var_set 'GOOGLE_CREDENTIALS_FOCUS'
        test_var_set 'GOOGLE_PLAY_SERVICE_ACCOUNT_REFERENCE_BROWSER'
        test_var_set 'GOOGLE_CREDENTIALS_REFERENCE_BROWSER'
        test_var_set 'GOOGLE_PLAY_SERVICE_ACCOUNT_FIREFOX_BETA'
        test_var_set 'GOOGLE_CREDENTIALS_FIREFOX_BETA'
        test_var_set 'GOOGLE_PLAY_SERVICE_ACCOUNT_FIREFOX_RELEASE'
        test_var_set 'GOOGLE_CREDENTIALS_FIREFOX_RELEASE'
        test_var_set 'AMAZON_CLIENT_ID'
        test_var_set 'AMAZON_CLIENT_SECRET'

        export GOOGLE_CREDENTIALS_FENIX_PROD_PATH=$CONFIG_DIR/fenix_prod.p12
        export GOOGLE_CREDENTIALS_FOCUS_PATH=$CONFIG_DIR/focus.p12
        export GOOGLE_CREDENTIALS_REFERENCE_BROWSER_PATH=$CONFIG_DIR/reference_browser.p12
        export GOOGLE_CREDENTIALS_FIREFOX_BETA_PATH=$CONFIG_DIR/beta.p12
        export GOOGLE_CREDENTIALS_FIREFOX_RELEASE_PATH=$CONFIG_DIR/release.p12

        echo $GOOGLE_CREDENTIALS_FENIX_PROD | base64 -d >        $GOOGLE_CREDENTIALS_FENIX_PROD_PATH
        echo $GOOGLE_CREDENTIALS_FOCUS | base64 -d >             $GOOGLE_CREDENTIALS_FOCUS_PATH
        echo $GOOGLE_CREDENTIALS_REFERENCE_BROWSER | base64 -d > $GOOGLE_CREDENTIALS_REFERENCE_BROWSER_PATH
        echo $GOOGLE_CREDENTIALS_FIREFOX_BETA | base64 -d >      $GOOGLE_CREDENTIALS_FIREFOX_BETA_PATH
        echo $GOOGLE_CREDENTIALS_FIREFOX_RELEASE | base64 -d >   $GOOGLE_CREDENTIALS_FIREFOX_RELEASE_PATH

        import_cert fennec-nightly $CERT_DIR/nightly.pem
        import_cert fennec-beta $CERT_DIR/release.pem
        import_cert fennec-production $CERT_DIR/release.pem
        import_cert fenix-nightly $CERT_DIR/fenix_nightly.pem
        import_cert fenix-beta $CERT_DIR/fenix_beta.pem
        import_cert fenix-production $CERT_DIR/fenix_production.pem
        import_cert focus $CERT_DIR/focus_release.pem
        import_cert reference-browser $CERT_DIR/reference_browser_release.pem
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  mozillavpn)
    case $ENV in
      dev|fake-prod)

        echo "dummy" > $CONFIG_DIR/fake_cert.p12
        export GOOGLE_CREDENTIALS_MOZILLAVPN_DEP_PATH=$CONFIG_DIR/fake_cert.p12

        # no dep signing for mozillavpn yet, so no import_cert
        ;;
      prod)
        test_var_set 'GOOGLE_PLAY_SERVICE_ACCOUNT_MOZILLAVPN'
        test_var_set 'GOOGLE_CREDENTIALS_MOZILLAVPN'

        export GOOGLE_CREDENTIALS_MOZILLAVPN_PATH=$CONFIG_DIR/mozillavpn.p12
        echo $GOOGLE_CREDENTIALS_MOZILLAVPN | base64 -d > $GOOGLE_CREDENTIALS_MOZILLAVPN_PATH

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
