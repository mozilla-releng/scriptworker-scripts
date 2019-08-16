#!/bin/bash
set -e

export JARSIGNER_KEY_STORE="/app/mozilla-android-keystore"
rm -f "$JARSIGNER_KEY_STORE"
# Generate a temporary password
JARSIGNER_KEY_STORE_PASSWORD=$(tr -cd '[:alnum:]' < /dev/urandom | fold -w30 | head -n1)
CERT_DIR=/app/files

function import_cert() {
        JARSIGNER_KEY_STORE_NAME=$1
        JARSIGNER_KEY_STORE_CERTIFICATE=$2
        keytool \
          -importcert \
          -noprompt \
          -alias $JARSIGNER_KEY_STORE_NAME \
          -file $JARSIGNER_KEY_STORE_CERTIFICATE \
          -keystore $JARSIGNER_KEY_STORE \
          -trustcacerts \
          -srcstorepass $JARSIGNER_KEY_STORE_PASSWORD \
          -deststorepass $JARSIGNER_KEY_STORE_PASSWORD
}

case $COT_PRODUCT in
  firefox)
    case $ENV in
      dev|fake-prod)
        test $GOOGLE_CREDENTIALS_FIREFOX_DEP
        export GOOGLE_CREDENTIALS_FIREFOX_DEP_PATH=$CONFIG_DIR/dep.p12
        echo $GOOGLE_CREDENTIALS_FIREFOX_DEP | base64 -d > $GOOGLE_CREDENTIALS_FIREFOX_DEP_PATH

        import_cert dep $CERT_DIR/dep.pem
        ;;
      prod)
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_FIREFOX_RELEASE
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_FIREFOX_BETA
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_FIREFOX_AURORA
        test $GOOGLE_CREDENTIALS_FIREFOX_RELEASE
        test $GOOGLE_CREDENTIALS_FIREFOX_BETA
        test $GOOGLE_CREDENTIALS_FIREFOX_AURORA

        export GOOGLE_CREDENTIALS_FIREFOX_RELEASE_PATH=$CONFIG_DIR/release.p12
        export GOOGLE_CREDENTIALS_FIREFOX_BETA_PATH=$CONFIG_DIR/beta.p12
        export GOOGLE_CREDENTIALS_FIREFOX_AURORA_PATH=$CONFIG_DIR/aurora.p12

        echo $GOOGLE_CREDENTIALS_FIREFOX_RELEASE | base64 -d >     $GOOGLE_CREDENTIALS_FIREFOX_RELEASE_PATH
        echo $GOOGLE_CREDENTIALS_FIREFOX_BETA | base64 -d >        $GOOGLE_CREDENTIALS_FIREFOX_BETA_PATH
        echo $GOOGLE_CREDENTIALS_FIREFOX_AURORA | base64 -d >      $GOOGLE_CREDENTIALS_FIREFOX_AURORA_PATH

        import_cert nightly $CERT_DIR/nightly.pem
        import_cert release $CERT_DIR/release.pem
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  mobile)
    case $ENV in
      dev|fake-prod)

        import_cert fenix $CERT_DIR/fenix_dep.pem
        import_cert focus $CERT_DIR/focus_dep.pem
        import_cert reference-browser $CERT_DIR/reference_browser_dep.pem

        ;;
      prod)
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_FENIX_NIGHTLY
        test $GOOGLE_CREDENTIALS_FENIX_NIGHTLY
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_FENIX_BETA
        test $GOOGLE_CREDENTIALS_FENIX_BETA
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_FENIX_PROD
        test $GOOGLE_CREDENTIALS_FENIX_PROD
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_FOCUS
        test $GOOGLE_CREDENTIALS_FOCUS
        test $GOOGLE_PLAY_SERVICE_ACCOUNT_REFERENCE_BROWSER
        test $GOOGLE_CREDENTIALS_REFERENCE_BROWSER

        export GOOGLE_CREDENTIALS_FENIX_NIGHTLY_PATH=$CONFIG_DIR/fenix_nightly.p12
        export GOOGLE_CREDENTIALS_FENIX_BETA_PATH=$CONFIG_DIR/fenix_beta.p12
        export GOOGLE_CREDENTIALS_FENIX_PROD_PATH=$CONFIG_DIR/fenix_prod.p12
        export GOOGLE_CREDENTIALS_FOCUS_PATH=$CONFIG_DIR/focus.p12
        export GOOGLE_CREDENTIALS_REFERENCE_BROWSER_PATH=$CONFIG_DIR/reference_browser.p12

        echo $GOOGLE_CREDENTIALS_FENIX_NIGHTLY | base64 -d >     $GOOGLE_CREDENTIALS_FENIX_NIGHTLY_PATH
        echo $GOOGLE_CREDENTIALS_FENIX_BETA | base64 -d >        $GOOGLE_CREDENTIALS_FENIX_BETA_PATH
        echo $GOOGLE_CREDENTIALS_FENIX_PROD | base64 -d >        $GOOGLE_CREDENTIALS_FENIX_PROD_PATH
        echo $GOOGLE_CREDENTIALS_FOCUS | base64 -d >             $GOOGLE_CREDENTIALS_FOCUS_PATH
        echo $GOOGLE_CREDENTIALS_REFERENCE_BROWSER | base64 -d > $GOOGLE_CREDENTIALS_REFERENCE_BROWSER_PATH

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
  *)
    exit 1
    ;;
esac
