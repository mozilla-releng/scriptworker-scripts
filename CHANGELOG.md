# Changelog
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [2.0.0] - 2017-10-23
### Added
- 100% test coverage
- Added branching in .coveragerc
- Added py36 testing in travis
- Added firefox and devedition paths
- Added `push-to-releases` support
- Added `RELEASE_EXCLUDE` list of regexes to avoid copying to `releases/`
- Added `release_beetmover_task_schema.json` for release schema
- Added `redo` dependency
- Added `copy_beets`, `list_bucket_objects`, functions
- Added `requirements-{dep,prod}.txt` for dephash dependency tracking.

### Changed
- `TEMPLATE_KEY_PLATFORMS` is now a standard dict, not a defaultdict
- scopes checking functions now append messages to raise on, rather than raising for each message.

### Fixed
- Removed hardcoded `tc_nightly` from balrog manifest; only it adds it on nightly actions. On release actions, it adds `tc_release`.
- `setup_logging` now uses `logging.INFO` if not `verbose`. It also reduces `botocore`, `boto3`, and `chardet` logging to `logging.INFO`.

### Removed
- Removed mozilla-aurora from `RELEASE_BRANCHES`
- Removed `push-to-staging` action

## [1.0.0] - 2017-08-28
### Added
- Changelog
- Support for partials in manifest production for downstream tasks
