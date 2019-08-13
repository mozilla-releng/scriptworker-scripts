#!/bin/bash
set -e


case $COT_PRODUCT in
  firefox)
    case $ENV in
      dev|fake-prod)
        test $GOOGLE_CREDENTIALS_FIREFOX_DEP
        export GOOGLE_CREDENTIALS_FIREFOX_DEP_PATH=$CONFIG_DIR/dep.p12
        echo $GOOGLE_CREDENTIALS_FIREFOX_DEP | base64 -d > $GOOGLE_CREDENTIALS_FIREFOX_DEP_PATH
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
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  mobile)
    case $ENV in
      dev|fake-prod)
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

export JARSIGNER_KEY_STORE="/app/mozilla-android-keystore"

# TODO: based on COT_PRODUCT and ENV we need to read from
#export JARSIGNER_KEY_STORE_CERTIFICATE=...
# TODO: dep, nightly, release, fenix, focus, reference-browser, fenix-nightly,
#       fenix-beta, fenix-production
#export JARSIGNER_KEY_STORE_NAME=...
# TODO: i dont think we need this
#export JARSIGNER_KEY_STORE_PASSWORD=...

#keytool \
#  -importcert \
#  -noprompt \
#  -alias $JARSIGNER_KEY_STORE_NAME \
#  -file $JARSIGNER_KEY_STORE_CERTIFICATE \
#  -keystore $JARSIGNER_KEY_STORE \
#  -trustcacerts \
#  # TODO: i don't think we need this
#  -srcstorepass $JARSIGNER_KEY_STORE_PASSWORD \
#  -deststorepass $JARSIGNER_KEY_STORE_PASSWORD
