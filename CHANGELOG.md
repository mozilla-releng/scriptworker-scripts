# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [3.2.0] - 2019-08-14

### Adds
* Any google play track now can be rolled out to (not just "production")

### Changes
* Deprecates `"google_play_track": "rollout"` and `"channel": "rollout"` in task payloads
* When "rollout" is still used, the target track will be set based on `google_play_track` set in config

## [3.1.0] - 2019-07-10

### Changes
* Removes obsolete `push_apk(...)` parameter

## [3.0.0] - 2019-07-09

### Removed
* Google Play strings publication

## [2.1.0] - 2019-06-06

### Changes
* In the task payload, `google_play_track` now explicitly overrides the track in Google Play, and `channel` is required to disambiguate between apps


## [2.0.0] - 2019-06-03

### Changes
* Structure of config to support both cases of "channels map to individual apps" and "channels map to Google Play tracks within a single app"

## [1.0.4] - 2019-05-13

### Fixes
* `certificate_alias` is now added to the schema


## [1.0.3] - 2019-05-07

### Added
* New task parameter `certificate_alias`: defines the specific certificate alias that should be used to verify the APK  to upload

## [1.0.2] - 2019-04-26

### Added
* New option `require_track`: forces any tasks matcheing the config to have the track defined in `require_track`


## [1.0.1] - 2019-04-12

###
* Support mozapkpublisher 2.0+


## [1.0.0] - 2019-03-29

### Changed
* Bumps version to `1.0.0` since `pushapkscript` is used in production

## [0.14.0] - 2019-02-13

### Added
* New options:
    * `digest_algorithm`: expected digest algorithm of signed app. Verified before app deployed to Google Play
    * `update_google_play_strings`: true if strings should be updated in Google Play for this app
    * `skip_checks_fennec`: passed to `mozapkpublisher`
    * `skip_check_ordered_version_codes`: passed to `mozapkpublisher`
    * `skip_check_multiple_locales`: passed to `mozapkpublisher`
    * `skip_check_same_locales`: passed to `mozapkpublisher`
    * `skip_check_package_names`: passed to `mozapkpublisher`
    * `has_nightly_track`: fails build if an APK is attempted to be pushed to `nightly` without having a `nightly track

### Changed
* In config, `google_play_accounts` is now called `products`

## [0.13.0] - 2019-02-01
### Added
* `do_not_contact_google_play` to instance config file

### Changed
* Now compatible with with `mozapkpublisher` > 0.14.0

## [0.12.0] - 2019-01-09

### Added
* Support pushing [`fenix`](https://github.com/mozilla-mobile/fenix) to Google Play

## [0.11.0] - 2019-01-02

### Changed
* `schema_file` is now specified internally and should no longer be set in configuration

## [0.10.1] - 2018-12-20

### Changed
* Authorizes reference-browser to be deployed to Google Play


## [0.10.0] - 2018-12-19

### Added
* Support pushing [`reference-browser`](https://github.com/mozilla-mobile/reference-browser)

### Changed
* Configuration: `taskcluster_scope_prefix` now becomes `taskcluster_scope_prefixes` and takes a JSON array.


## [0.9.0] - 2018-11-23

### Changed
* Digest algorithm is not checked by jarsigner anymore. Instead, pushapkscript parses `META-INF/MANIFEST.MF`. This allows several digests to be used. Otherwise jarsigner inconsistently reports one of the digests.


## [0.8.0] - 2018-06-22

### Removed
* Python 3.5 support

### Added
* Python 3.7 support

### Changed
* `google_play_track` in task payload can now be a random string. Value is enforced by mozapkpublisher.


## [0.7.0] - 2018-04-27

### Added
* Support for Firefox Focus
* Support for Google Play's new internal track.


## [0.6.0] - 2018-04-20

### Removed
* Removed architecture detection. It's now delegated in mozapkpublisher.

### Changed
* Updated mozapkpublisher call to match new function signature


## [0.5.0] - 2018-03-19

### Changed
* `script.async_main()` relies on scriptworker (>= 10.2.0) to:
 * initialize context, config, and task
 * validate the task schema
 * `exceptions.TaskVerificationError` in favor of the one in scriptworker
 * `script.usage()` now handled by scriptworker
 * `task.validate_task_schema()` now handled by scriptworker

### Removed
* Now that Firefox 59 is on release:
 * `dry_run` is not accepted anymore in task payload
 * strings aren't fetched anymore by this worker type


## [0.4.1] - 2018-01-03

### Added
* Google Play strings are now optionally fetched from an upstream task.


## [0.4.0] - 2017-11-29

### Removed
* Deprecated `payload.dry_run` in favor of `payload.commit` in task definition

### Added
* Add support of dep-signing. dep-signing is used by testing APKs. pushapkscript won't make a single request to Google Play if such APK is detected.


## [0.3.4] - 2017-06-19

### Added
* APK verification now includes a pass on the digest algorithm


## [0.3.3] - 2017-05-31

### Added
* FAQ
* Dawn project: Allow "aurora" scope to be still used in task definition
* Support different architectures depending on which channel we are


## [0.3.2] - 2017-04-11

### Fixed
* Task validation which refused a payload with `dry_run` in it


## [0.3.1] - 2017-04-10

### Added
* Tasks can now define a rollout percentage for the rollout track


## [0.3.0] - 2017-03-30

### Changed
* Artifacts are downloaded thanks to Chain of Trust
* APK architectures don't need to be manually input. They are now automatically detected.


## [0.2.2] - 2017-02-10

### Changed
* Pin dependencies in Puppet only.
* Use new tc-migrated build locations.


## [0.2.1] - 2017-01-27

### Changed
* Upgrade to scriptworker v2.0.0 (without Chain of Trust), which reports errors back to Treeherder.


## [0.2.0] - 2017-01-20

### Changed
* Upgrade to scriptworker v1.0.0b7 (without Chain of Trust). Please update your config accordingly to the new config_example.json


## [0.1.4] - 2016-11-09

### Changed
* Mute debug logs of oauth2client


## [0.1.3] - 2016-11-09

### Changed
* APKs are not committed onto Google Play Store, by default anymore.


## [0.1.2] - 2016-10-25

### Fixed
* Use scriptworker 0.7.2 which notably fixes how message_info['task_info'] is used.  A new property called "hintId" broke a function call.


## [0.1.1] - 2016-10-06

### Fixed
* Fix package missing files


## [0.1.0] - 2016-10-05
Initial release
