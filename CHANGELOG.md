# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## X.Y.Z] - TODO
### Removed
- `thunderbird-next-latest` and `thunderbird-next-latest-ssl` as valid regexes since they are being unused

## [3.5.0] - 2019-01-25
### Added
- Add win64-aarch64 support for release bouncer entries.

## [3.4.1] - 2019-01-14
### Added
- Added support for aarch64 in bouncer location nightly jobs

## [3.4.0] - 2019-01-02
### Changed
* `schema_file` is now specified internally and should no longer be set in configuration

## [3.3.0] - 2018-11-12
### Added
- Added support for new locations for MSI installers

## [3.2.1] - 2018-09-04
### Fixed
- Bouncer products with multiple platforms that share paths (i.e. stubs) now
  have both platforms properly populated.

## [3.2.0] - 2018-09-04
### Added
- Added new behavior `bouncer-locations` for `bouncerscript` to handle
- Add checks for locations during `bouncer-submission` phase


## [3.1.0] - 2018-08-28
### Added
- Added a SCOPES.md file in repo root to document the relevant scopes used in bouncerscript

### Fixed
- Fixed `bouncer-submission` support for Firefox RC paths.


## [3.0.0] - 2018-07-11
### Added
- Add support for `bouncer-submission` data validations *before* and *after* bouncer API calls
- Add support for `bouncer-aliases` data validations *before* and *after* bouncer API calls
- more verbose logging

### Fixed
- fixed coveralls and coverage back to 100%

## Removed
- stopped using scriptworker event_loop fixture


## [2.0.0] - 2018-06-05
### Added
- Support for thunderbird scope prefixes.
- Support for `*-ssl` prefixes for thunderbird.
- Support for `thunderbird-next-*` prefixes for initial esr60 release.


## [1.3.0] - 2018-05-03
### Added
- Support of `firefox-esr-next-latest` and `firefox-esr-next-latest-ssl` aliases


## [1.2.1] - 2018-03-21
### Added
- bouncer aliases preflight checks - making sure the aliases match certain regexes


## [1.1.0] - 2018-03-19
### Changed
- `script.async_main()` relies on scriptworker (>= 10.2.0) to initialize context, config, and task
- `task.validate_task_schema()` now relies on scriptworker


## Removed
- `script.usage()`, now handled by scriptworker
- `task.validate_task_schema()` now handled by scriptworker
- `load_json` now handled by scriptworker (moved it temporarily under tests until integration tests are added)


## [1.0.0] - 2018-03-12
### Added
- changelog
- 100% code-coverage
- production mode for bouncerscript
