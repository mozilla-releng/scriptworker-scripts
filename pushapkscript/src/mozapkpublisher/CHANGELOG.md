# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [10.0.1] - 2025-07-01

### Fixed

* Uploading apks to Samsung Galaxy Store will now use a unique file name as the store doesn't like name reuse. This change is transparent as the API never uses the file name to refer to a file.

## [10.0.0] - 2025-06-18

### Changed

* `push_apk` no longers submits the samsung udpates automatically. Use `--submit` to keep the old behavior.
* The androguard dependency has been replaced with pyaxmlparser to reduce the number of transitive dependencies pulled by mozapkpublisher

### Removed

* `mozapkpublisher.common.utils.is_firefox_version_nightly` is no more. It was using some very out of date way of checking for that and wasn't used anywhere.

## [9.0.1] - 2025-06-02

### Fixed

* `dry_run` runs won't try to contact the samsung galaxy store at all anymore if the target store is samsung

## [9.0.0] - 2025-06-02

### Changed

* `push_apk` and `push_aab` are now async functions. If you're using it from a sync function, you can wrap them with `asyncio.run`.

## [8.0.0] - 2025-05-21

### Added

* Added support for pushing APKs to the Samsung Galaxy Store

### Removed

* Removed `get_apk.py`
* Dropped support for python 3.8, 3.9 and 3.10

## [7.0.0] - 2023-11-17

### Changed
* Switched Google Play Store authentication to the google-auth library.  The credentials now need to be passed as a json file instead of an email address and PKCS#12 file.

## [6.3.0] - 2023-11-08

### Removed
* Removed support for pushing to the Amazon store.

### Fixed
* Better diagnostics during AAB upload

## [6.2.1] - 2023-09-21

### Fixed
* Specify media mime type for AAB uploads

## [6.2.0] - 2023-09-11

### Added
* AAB support

## [6.1.1] - 2020-03-12

### Fixed
* Publication to the Google Play Store: the track is now required in both the URL and the body of the request.

## [6.1.0] - 2019-09-26

### Added
* Push to Amazon support


## [6.0.0] - 2019-09-24

### Fixed
* Focus and Klar were sent in the same transaction, which cannot happen.
* False positive exception about multiple architectures

### Removed
* `update_apk_description.py`: https://l10n.mozilla-community.org/stores_l10n/ is now retired making the script useless.
* `get_l10n_strings.py`: Automation hasn't used this script since [Bug 1560876](https://bugzilla.mozilla.org/show_bug.cgi?id=1560876). Moreover, like `update_apk_description.py`, this script doesn't work anymore.
* Exceptions `TranslationMissingData`, `NoTranslationGiven` which aren't used anymore


## [5.0.0] - 2019-08-14

### Added
* Any track can now be targeted with rollout

### Changed
* Using `track="rollout"` is now deprecated (specify the target track instead)
* Uses RAII to represent operations that require an "edit"

## [4.1.0] - 2019-07-10
### Removed
* `--skip-check-package-names`. When pushing or checking an APK, expected package names must always be provided

## [4.0.0] - 2019-07-09
### Changed
* `EditService` now calls the Google Play API v3
* Fennec Beta can now match 68.Y pattern

### Fixed
* Support new GP error when an APK is uploaded

### Removed
* `push_apk.py` does not upload strings (like `description` or `whatsnew`) because https://l10n.mozilla-community.org/stores_l10n/ is about to be removed. `update_apk_description.py` remains in case we still want a manual upload while `stores_l10n` is around


## [3.1.0] - 2019-05-28
### Added
* Fennec ARM64 push on Release.


## [3.0.0] - 2019-05-28
### Changed
* `push_apk` doesn't error out anymore if an APK has already been uploaded

### Removed
* Python 3.5 support


## [2.0.2] - 2019-04-22
### Fixed
* When multiple package names were used, packages weren't filtered properly


## [2.0.1] - 2019-04-12
### Fixed
* Missing tar.gz package which was missing due to a pypi error


## [2.0.0] - 2019-04-10

### Added
* `check_apks.py`. This script runs the same checks as `push_apk.py`
* Allow AArch64 on Fennec Nightly and Beta only

### Removed
* Fennec checks no longer implicitly check that all packages have the same name, but rather lean on `--expected-package-name`


## [1.0.1] - 2019-02-12

### Added
* x86_64 push

## [1.0.0] - 2019-02-11

### Added
* Options to skip specific sanity checks
    * `--skip-check-ordered-version-codes`: Skip check that asserts version codes are different, x86 code > arm code
    * `--skip-check-multiple-locales`: Skip check that asserts that apks all have multiple locales
    * `--skip-check-same-locales`: Skip check that asserts that all apks have the same locales
    * `--skip-checks-fennec`: Skip checks that are Fennec-specific (ini-checking, checking version-to-package-name compliance)
    * `--skip-check-package-names`: Skip assertion that apks match a specified package name
        * Note: if this isn't provided, then you must provide at least one `--expected-package-name`

## [0.14.1] - 2019-02-12

**Note: This was released in a branch off of `0.14.0`! These changes don't exist in `1.0.0`**

### Added
* x86_64 push

## [0.14.0] - 2019-01-29

### Changed
* `push_apk` must be called as a function with parameters, rather than mocked `argv` arguments* Refactors `push_apk` to use a variable Google Play Strings interface  

### Removed
* Auto-detection of which package-name corresponds to which sanity checks

## [0.13.0] - 2019-01-15

### Fixed
* AArch64 push

### Added
* Allow an architecture to not share the same API levels with others.

## [0.12.0] - 2019-01-14

### Added
* Allow AArch64 on Fennec Nightly only

## [0.11.0] - 2019-01-09

### Added
* Support pushing [`fenix`](https://github.com/mozilla-mobile/fenix)

## [0.10.1] - 2018-12-20

### Fixed
* Reference Browser doesn't try to find `firefox_version` anymore.

## [0.10.0] - 2018-12-19

### Fixed
* Nightly en-US releases are downloadable

### Added
* Support pushing [`reference-browser`](https://github.com/mozilla-mobile/reference-browser)
* APK Downloads now happen in parallel


## [0.9.2] - 2018-11-08

### Fixed
* Added requirements.txt.in in package so setup.py works


## [0.9.1] - 2018-11-07

## Fixed
* `setup.py` gets better formatted requirements. This avoids pip install errors.

## [0.9.0] - 2018-10-19

### Changed
* requirements are now split in several files depending on whether they're for testings, coveralls or production

### Added
* Python 3.7 support

### Removed
* `get_l10n_strings`: `--major-version-number`

## [0.8.0] - 2018-06-22

### Fixed
* `get_apk.py` can download Firefox releases and bets >= 59. Nightly is known to be broken because of https://bugzilla.mozilla.org/show_bug.cgi?id=1469303.

### Changed
* `push_apk.py` now supports custom Google Play tracks. Allowed tracks are defined per product and must be whitelisted in `googleplay.py`.


## [0.7.2] - 2018-05-04

### Added
* get_l10n_strings: `--major-version-number` option to fetch `whatsnew` section from a specific version instead of a channel. This is particularly useful in the context of Release Candidates, when you want to update listings as they used to be, but get the latest `whatsnew`.


## [0.7.1] - 2018-04-30

### Fixed
* Remove unneeded check for distinct package names which broke Klar+GeckoView upload

## [0.7.0] - 2018-04-27

### Added
* Support Google Play's new `internal` track
* Support Firefox Focus/Klar APKs. Specific tests for these APKs were added.


## [0.6.0] - 2018-04-20

### Changed
* `push_apk()` has its command line arguments changed.
  * There is no need to precise the package name and the architecture anymore. These values are automatically extracted and checked from the passed APKs. As a consequence, APKs are now (unordered) positional arguments.
  * `--track` is now required and doesn't default to `alpha` anymore.

### Added
* More data is extracted from APKs and checked.
  * Namely: processor architecture, Firefox version, Firefox buildId, locales, Android package name, Android API level, Android version code.
  * `mozapkpublisher.apk` was split in favor of `mozapkpublisher.apk.{extractor,checker}`
  * `mozapkpublisher.apk.extractor` relies on androguard to extract Android specific data
  * It works with a copy of the APKs, in the (very unlikely) case the APK gets modified by the extracting function
  * `mozapkpublisher.apk.checker` verifies the common values are all identical and the different ones are correctly order and none is missing.
* `Base` parser now accepts positional arguments in parameters dictionary. They must be filled as `{'*args': [positional_arg_1, positional_arg_2, positional_arg_3]}`


## [0.5.0] - 2017-11-28

### Removed
* Python 2 support has been droppped. Handling unicode strings in both Python 2 and 3 became too risky for the [pros Python 2 gave](https://github.com/mozilla-releng/mozapkpublisher/pull/45).

### Added
* get_l10n_strings.py now exists. It fetches strings from the Google Play store for later use (by push_apk.py).

### Changed
* push_apk.py
  * You now need to provide where the Google Play linsting are taken from (`--update-gp-strings-from-l10n-store`, `--update-gp-strings-from-file`, or even `--no-gp-string-update`).
  * Google Play strings are now verified: Data structure must comply to a given schema. Actual strings aren't checked.
  * Option `--dry-run` becomes `--commit`. By default, no transaction is committed.
  * Option `--do-not-contact-google-play` was added. It allows to run the script without making any call to Google.
* Non-script files are moved to `mozapkpublisher/common.`


## [0.4.0] - 2017-05-31

### Changed
* Dawn project
  * Publish Nightly on top of Aurora
  * Fetch and upload Nightly listings/recent changes
  * Optimize network requests on both stores_l10n and Google Play ends
  * Remove the ability to download Aurora APKs


## [0.3.1] - 2017-05-22

### Fixed
* get_apk.py: Fix checksum detection when file is in a subfolder


## [0.3.0] - 2017-05-16

### Changed
* Upgrade upstream dependencies


## [0.2.3] - 2017-04-21

### Added
* Verifies if `rollout_percentage` is actually used on the rollout channel. Without it, you may go full rollout, like explained in [bug 1354038 comment 2](https://bugzilla.mozilla.org/show_bug.cgi?id=1354038#c2)


## [0.2.2] - 2017-03-30

### Changed
* Upgrade requests package


## [0.2.1] - 2017-03-28

### Fixed
* Python 2: Fix encoding issue when uploading locales that contain non-ASCII characters


## [0.2.0] - 2017-03-24

### Changed
* push_apk.py first publishes listing then "what's new". This fixes unsupported locales described in [bug 1349039](https://bugzilla.mozilla.org/show_bug.cgi?id=1349039)
* get_apk.py doesn't break because files are internally renamed after being downloaded

### Removed
* get_apk.py: `--clean`


## [0.1.6] - 2017-03-09

### Added
* Check if version codes are correctly ordered
* get_apk.py supports checksum files for Fennec >= 53.0b1

### Changed
* en-GB is now updated like any other locale


## [0.1.5] - 2017-01-20

### Changed
* Upgrade pyOpenSSL, in order to keep support for OpenSSL v1.1.0


## [0.1.4] - 2017-01-09

### Changed
* Use new store_l10n APIs

### Added
* New installation instructions for OS X
* Better logs
* Test coverage


## [0.1.3] - 2016-11-09

### Added
* Check to prevent single locale APKs to be pushed ([bug 1314712](https://bugzilla.mozilla.org/show_bug.cgi?id=1314712))
* --dry-run flag

### Changed
* Mute some debug logs coming from dependencies


## [0.1.2] - 2016-09-28

### Fixed
* Other missing files in package


## [0.1.1] - 2016-09-28

### Fixed
* Missing files in final package


## [0.1.0] - 2016-09-28
* Initial release
