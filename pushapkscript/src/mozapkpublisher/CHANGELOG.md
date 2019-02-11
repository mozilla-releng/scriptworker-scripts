# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [upcoming]

### Added
* Options to skip specific sanity checks
    * `--skip-check-ordered-version-codes`: Skip check that asserts version codes are different, x86 code > arm code
    * `--skip-check-multiple-locales`: Skip check that asserts that apks all have multiple locales
    * `--skip-check-same-locales`: Skip check that asserts that all apks have the same locales
    * `--skip-checks-fennec`: Skip checks that are Fennec-specific (ini-checking, checking version-to-package-name compliance)
    * `--skip-check-package-names`: Skip assertion that apks match a specified package name
        * Note: if this isn't provided, then you must provide at least one `--expected-package-name`

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
