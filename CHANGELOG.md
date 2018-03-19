# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [3.0.0]
### Changed
- switched to V9 Creator and Submitter for releases

## [2.0.0]
### Added
- added `balrogscript.constants` module
- added support for `submit-toplevel` and `schedule` actions, for releases.

### Changed
- the `schema_file` string is now a `schema_files` dict in config.
- the `submit` action is now `submit-locale`.
- `create_submitter` is now `create_locale_submitter`
- revamped the requirements files.

### Removed
- removed channel scope support; these weren't fully fleshed out.

## [1.1.0] - 2018-01-09
### Added
- `IOError` as part of caught exceptions in `load_config` for file not found issues
- in testing: release-type manifest, release-type tasks, release-type behaviors
- 100% test coverage

### Changed
- `upstream_artifacts` are no longer baked within the rest of `configs` because it's counter-intuitive. They lay separately in a variable now and play along with the `task` definition

### Fixed
- `task.json` config is now up-to-date with the release-type changes.
- `api_root` now lies within the server configurations rather than outside
- release manifest sample in testing is now up-to-date

### Removed
- `boto` logger as it is not used
- `KeyError` exception from `load_config` function as no behavior could lead there

## [1.0.0] - 2017-12-14
### Added
- Changelog
- Support for processing release manifest from beetmover

### Fixed
- fixed some logging
